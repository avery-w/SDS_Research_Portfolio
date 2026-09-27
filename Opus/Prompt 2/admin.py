"""Admin area: users, stores, products, orders, platform settings, audit log and analytics."""
from datetime import date, timedelta

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from sqlalchemy import func, or_

from core import Form, audit, require, safe_next, set_item_status
from models import (ITEM_STATUSES, RESTOCKED, REVENUE_STATUSES, ROLES, SETTINGS, AuditLog, Order, OrderItem, Product,
                    Setting, Store, User, db, setting)
from seller import revenue_by_day, top_products
from shop import change_item

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
@require("admin")
def guard():
    """Every /admin route is admin-only: 302 to login when signed out, 403 for other roles."""


@bp.get("")
def dashboard():
    since = date.today() - timedelta(days=29)
    live = OrderItem.status.in_(REVENUE_STATUSES)
    line = OrderItem.unit_price_cents * OrderItem.qty
    gross_all = db.session.query(func.coalesce(func.sum(line), 0)).filter(live).scalar()
    gross_30 = db.session.query(func.coalesce(func.sum(line), 0)).select_from(OrderItem).join(Order).filter(
        live, Order.created_at >= since).scalar()
    orders_30 = Order.query.filter(Order.created_at >= since).count()
    commission = setting("commission_pct")
    by_status = dict(db.session.query(OrderItem.status, func.count()).group_by(OrderItem.status).all())
    top_stores = (db.session.query(Store.name, func.sum(line)).join(OrderItem, OrderItem.store_id == Store.id)
                  .filter(live).group_by(Store.id).order_by(func.sum(line).desc()).limit(5).all())
    by_category = (db.session.query(Product.category, func.sum(line)).join(OrderItem, OrderItem.product_id == Product.id)
                   .filter(live).group_by(Product.category).order_by(func.sum(line).desc()).all())
    users = dict(db.session.query(User.role, func.count()).group_by(User.role).all())
    return render_template(
        "admin/dashboard.html", series=revenue_by_day(), gross_all=gross_all, gross_30=gross_30,
        orders_30=orders_30, aov=round(gross_30 / orders_30) if orders_30 else 0,
        commission_30=round(gross_30 * commission / 100), commission=commission,
        new_users=User.query.filter(User.created_at >= since).count(), users=users,
        by_status=[(s, by_status.get(s, 0)) for s in ITEM_STATUSES], top=top_products(),
        top_stores=top_stores, by_category=by_category,
        recent=AuditLog.query.order_by(AuditLog.id.desc()).limit(8).all())


# ---------- users ----------

@bp.get("/users")
def users():
    q, role = request.args.get("q", "").strip()[:100], request.args.get("role")
    query = User.query
    if q:
        query = query.filter(or_(User.email.ilike(f"%{q}%"), User.name.ilike(f"%{q}%")))
    if role in ROLES:
        query = query.filter_by(role=role)
    page = query.order_by(User.id.desc()).paginate(page=max(request.args.get("page", 1, type=int), 1),
                       per_page=25, error_out=False)
    return render_template("admin/users.html", page=page, roles=ROLES)


@bp.post("/users/new")
def create_user():
    f = Form(request.form)
    name, email = f.str("name", "Name", max_len=100), f.email()
    pw = f.str("password", "Password", min_len=8, max_len=128)
    role = f.choice("role", ROLES, "Role")
    if email and User.query.filter_by(email=email).first():
        f.errors["email"] = "An account with that email already exists."
    f.done()
    u = User(name=name, email=email, role=role)
    u.set_password(pw)
    db.session.add(u)
    audit("user.create", f"{email} as {role}")
    db.session.commit()
    flash(f"Created {role} account for {email}.", "success")
    return redirect(url_for("admin.users"))


@bp.post("/users/<int:uid>")
def update_user(uid):
    u = db.get_or_404(User, uid)
    f = Form(request.form)
    action = f.choice("action", ["activate", "deactivate", "set_role"], "Action")
    role = f.choice("role", ROLES, "Role") if action == "set_role" else None
    f.done()
    if u.id == g.user.id:
        abort(409, "You can't deactivate or demote your own admin account.")
    if action == "set_role":
        if role == "customer" and u.store:
            abort(409, "This user owns a store. Suspend the store instead of removing the seller role.")
        u.role = role
    else:
        u.is_active = action == "activate"
    audit(f"user.{action}", f"{u.email}" + (f" -> {role}" if role else ""))
    db.session.commit()
    flash(f"{u.email}: {action.replace('_', ' ')}{' ' + role if role else ''}.", "success")
    return redirect(safe_next(request.form.get("next"), url_for("admin.users")))


# ---------- stores & products ----------

@bp.get("/stores")
def stores():
    rows = (db.session.query(Store, func.count(Product.id)).outerjoin(Product).group_by(Store.id)
            .order_by(Store.id.desc()).all())
    return render_template("admin/stores.html", rows=rows)


@bp.post("/stores/<int:sid>/toggle")
def toggle_store(sid):
    s = db.get_or_404(Store, sid)
    s.is_active = not s.is_active
    audit("store." + ("reinstate" if s.is_active else "suspend"), s.name)
    db.session.commit()
    flash(f"{s.name} {'reinstated' if s.is_active else 'suspended'}.", "success")
    return redirect(url_for("admin.stores"))


@bp.get("/products")
def products():
    q = request.args.get("q", "").strip()[:100]
    query = Product.query.join(Store)
    if q:
        query = query.filter(or_(Product.name.ilike(f"%{q}%"), Store.name.ilike(f"%{q}%")))
    page = query.order_by(Product.id.desc()).paginate(page=max(request.args.get("page", 1, type=int), 1),
                       per_page=25, error_out=False)
    return render_template("admin/products.html", page=page)


@bp.post("/products/<int:pid>/toggle")
def toggle_product(pid):
    """Takedown locks the listing so the seller can't re-list it; reinstating unlocks it."""
    p = db.get_or_404(Product, pid)
    p.locked = p.is_active
    p.is_active = not p.is_active
    audit("product." + ("reinstate" if p.is_active else "takedown"), f"#{p.id} {p.name}")
    db.session.commit()
    flash(f"{p.name} {'reinstated' if p.is_active else 'taken down'}.", "success")
    return redirect(safe_next(request.form.get("next"), url_for("admin.products")))


# ---------- orders ----------

@bp.get("/orders")
def orders():
    status = request.args.get("status")
    query = Order.query
    if status in ITEM_STATUSES:
        query = query.filter(Order.items.any(OrderItem.status == status))
    q = request.args.get("q", "").strip()
    if q.isdigit():
        query = query.filter(Order.id == int(q))
    elif q:
        query = query.join(User).filter(User.email.ilike(f"%{q[:100]}%"))
    page = query.order_by(Order.id.desc()).paginate(page=max(request.args.get("page", 1, type=int), 1),
                       per_page=25, error_out=False)
    return render_template("admin/orders.html", page=page, statuses=ITEM_STATUSES, status=status)


@bp.post("/order-items/<int:iid>/status")
def override_item(iid):
    f = Form(request.form)
    status = f.choice("status", ITEM_STATUSES, "Status")
    f.done()
    item = change_item(iid, status, request.form)
    flash(f"Override applied: {item.name} is now {status.replace('_', ' ')}.", "success")
    return redirect(url_for("shop.order", oid=item.order_id))


@bp.post("/orders/<int:oid>/cancel")
def force_cancel(oid):
    o = db.get_or_404(Order, oid)
    items = [i for i in o.items if i.status not in RESTOCKED]
    if not items:
        abort(409, "Every item on this order is already cancelled or returned.")
    for i in items:
        set_item_status(i, "cancelled", "admin", override=True)
    audit("order.force_cancel", f"order {o.id} ({len(items)} items)")
    db.session.commit()
    flash(f"Order #{o.id} cancelled and stock restored.", "success")
    return redirect(url_for("shop.order", oid=o.id))


# ---------- settings & audit ----------

@bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        f = Form(request.form)
        values = {}
        for key, (_, typ, label) in SETTINGS.items():
            if typ is str:
                values[key] = f.str(key, label, required=key != "announcement", max_len=200)
            elif typ is int:
                values[key] = f.int(key, label, lo=0, hi=365)
            else:
                values[key] = f.number(key, label, lo=0, hi=100)
        f.done()
        for key, v in values.items():
            row = db.session.get(Setting, key) or Setting(key=key)
            row.value = str(v)
            db.session.add(row)
        audit("settings.update", ", ".join(f"{k}={v}" for k, v in values.items())[:500])
        db.session.commit()
        flash("Platform settings saved.", "success")
        return redirect(url_for("admin.settings"))
    return render_template("admin/settings.html", settings=SETTINGS)


@bp.get("/audit")
def audit_log():
    page = AuditLog.query.order_by(AuditLog.id.desc()).paginate(
        page=max(request.args.get("page", 1, type=int), 1), per_page=50, error_out=False)
    return render_template("admin/audit.html", page=page)
