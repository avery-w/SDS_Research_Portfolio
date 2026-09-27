from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func, or_, select

from .auth import role_required
from .models import NOT_REVENUE, ORDER_STATUSES, ROLES, SETTING_DEFAULTS, Order, Product, Setting, Store, User, db, get_setting, sales_summary

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@role_required("admin")
def dashboard():
    stats = sales_summary()
    commission_pct = float(get_setting("commission_pct") or 0)
    top_stores = db.session.execute(
        select(Store.name, func.sum(Order.subtotal_cents).label("revenue"), func.count(Order.id))
        .join(Order)
        .where(Order.status.not_in(NOT_REVENUE))
        .group_by(Store.id, Store.name)
        .order_by(func.sum(Order.subtotal_cents).desc())
        .limit(5)
    ).all()
    counts = {
        "users": dict(db.session.execute(select(User.role, func.count()).group_by(User.role)).all()),
        "stores": db.session.scalar(select(func.count()).select_from(Store).where(Store.active)),
        "products": db.session.scalar(select(func.count()).select_from(Product).where(Product.active)),
    }
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        commission_cents=round(stats["subtotal_cents"] * commission_pct / 100),
        commission_pct=commission_pct,
        top_stores=top_stores,
        counts=counts,
    )


@bp.route("/users")
@role_required("admin")
def users():
    q = request.args.get("q", "").strip()
    stmt = select(User).order_by(User.created_at.desc())
    if q:
        stmt = stmt.where(or_(User.email.ilike(f"%{q}%"), User.name.ilike(f"%{q}%")))
    return render_template("admin/users.html", page=db.paginate(stmt, per_page=50, error_out=False), q=q, roles=ROLES)


@bp.route("/users/<int:user_id>", methods=["POST"])
@role_required("admin")
def user_update(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("You can't change your own role or status.", "error")
        return redirect(url_for("admin.users"))
    if request.form.get("role") in ROLES:
        user.role = request.form["role"]
    user.active = request.form.get("active") == "1"  # a deactivated seller's products disappear from the shop
    db.session.commit()
    flash(f"Updated {user.email}.", "success")
    return redirect(request.referrer or url_for("admin.users"))


@bp.route("/stores")
@role_required("admin")
def stores():
    return render_template("admin/stores.html", stores=list(db.session.scalars(select(Store).order_by(Store.name))))


@bp.route("/stores/<int:store_id>", methods=["POST"])
@role_required("admin")
def store_update(store_id):
    store = db.get_or_404(Store, store_id)
    store.active = request.form.get("active") == "1"
    name = request.form.get("name", "").strip()
    if name and not db.session.scalar(select(Store).where(Store.name == name, Store.id != store.id)):
        store.name = name
    db.session.commit()
    flash(f"Updated store {store.name}.", "success")
    return redirect(url_for("admin.stores"))


@bp.route("/products")
@role_required("admin")
def products():
    q = request.args.get("q", "").strip()
    stmt = select(Product).order_by(Product.created_at.desc())
    if q:
        stmt = stmt.where(Product.name.ilike(f"%{q}%"))
    return render_template("admin/products.html", page=db.paginate(stmt, per_page=50, error_out=False), q=q)


@bp.route("/products/<int:product_id>/toggle", methods=["POST"])
@role_required("admin")
def product_toggle(product_id):
    p = db.get_or_404(Product, product_id)
    p.active = not p.active
    db.session.commit()
    flash(f"{p.name} is now {'active' if p.active else 'hidden'}.", "success")
    return redirect(request.referrer or url_for("admin.products"))


@bp.route("/orders")
@role_required("admin")
def orders():
    status = request.args.get("status", "")
    stmt = select(Order).order_by(Order.created_at.desc())
    if status in ORDER_STATUSES:
        stmt = stmt.filter_by(status=status)
    return render_template("orders.html", orders=list(db.session.scalars(stmt.limit(500))), title="All orders", status=status, statuses=ORDER_STATUSES)


@bp.route("/orders/<int:order_id>", methods=["POST"])
@role_required("admin")
def order_override(order_id):
    """Admins may move an order to any status, overriding seller and customer rules."""
    o = db.get_or_404(Order, order_id)
    try:
        o.set_status(request.form.get("status", ""))
        o.tracking_number = request.form.get("tracking_number", o.tracking_number).strip()[:60]
        db.session.commit()
        flash(f"Order #{o.id} set to {o.status.replace('_', ' ')}.", "success")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "error")
    return redirect(url_for("shop.order", order_id=o.id))


@bp.route("/settings", methods=["GET", "POST"])
@role_required("admin")
def settings():
    if request.method == "POST":
        try:
            if not 0 <= float(request.form.get("commission_pct", "0")) <= 100:
                raise ValueError
        except ValueError:
            flash("Commission must be a number from 0 to 100.", "error")
            return redirect(url_for("admin.settings"))
        for key in SETTING_DEFAULTS:
            row = db.session.get(Setting, key) or Setting(key=key)
            row.value = request.form.get(key, "").strip()
            db.session.add(row)
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("admin.settings"))
    return render_template("admin/settings.html", values={k: get_setting(k) for k in SETTING_DEFAULTS})
