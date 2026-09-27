from datetime import timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func, or_, select

from auth import role_required
from models import (DEFAULT_SETTINGS, REVENUE_STATUSES, ROLES, STATUSES, Order, OrderItem, Product, Setting, Store,
                    User, db, get_setting, now)

bp = Blueprint("admin", __name__, url_prefix="/admin")
TABS = ("analytics", "users", "stores", "products", "orders", "settings")
MODELS = {"user": User, "store": Store, "product": Product}


def analytics():
    revenue = Order.status.in_(REVENUE_STATUSES)
    gross, count = db.session.execute(select(func.coalesce(func.sum(Order.total_cents), 0), func.count(Order.id)).where(revenue)).one()
    since = now() - timedelta(days=30)
    day = func.date(Order.created_at)
    return {
        "gross": gross,
        "orders": count,
        "aov": gross // count if count else 0,
        "commission": round(gross * float(get_setting("commission_pct")) / 100),
        "by_status": db.session.execute(select(Order.status, func.count()).group_by(Order.status)).all(),
        "daily": db.session.execute(
            select(day, func.count(), func.sum(Order.total_cents)).where(revenue, Order.created_at >= since)
            .group_by(day).order_by(day)).all(),
        "top_products": db.session.execute(
            select(OrderItem.name, func.sum(OrderItem.quantity).label("units"), func.sum(OrderItem.quantity * OrderItem.price_cents))
            .join(Order).where(revenue).group_by(OrderItem.product_id, OrderItem.name)
            .order_by(func.sum(OrderItem.quantity).desc()).limit(10)).all(),
        "top_stores": db.session.execute(
            select(Store.name, func.count(Order.id), func.sum(Order.subtotal_cents).label("rev"))
            .join(Order).where(revenue).group_by(Store.id, Store.name)
            .order_by(func.sum(Order.subtotal_cents).desc()).limit(10)).all(),
        "users": db.session.execute(select(User.role, func.count()).group_by(User.role)).all(),
    }


@bp.get("/")
@role_required("admin")
def index():
    tab = request.args.get("tab", "analytics")
    if tab not in TABS:
        abort(404)
    q = request.args.get("q", "").strip()[:100]
    ctx = {"tab": tab, "q": q, "roles": ROLES, "statuses": STATUSES}
    if tab == "analytics":
        ctx["a"] = analytics()
    elif tab == "users":
        stmt = select(User).order_by(User.id.desc())
        if q:
            stmt = stmt.where(or_(User.email.contains(q.lower(), autoescape=True), User.name.contains(q, autoescape=True)))
        ctx["rows"] = db.paginate(stmt, per_page=50)
    elif tab == "stores":
        ctx["rows"] = db.paginate(select(Store).order_by(Store.id.desc()), per_page=50)
    elif tab == "products":
        stmt = select(Product).order_by(Product.id.desc())
        if q:
            stmt = stmt.where(Product.name.contains(q, autoescape=True))
        ctx["rows"] = db.paginate(stmt, per_page=50)
    elif tab == "orders":
        stmt = select(Order).order_by(Order.created_at.desc())
        if (status := request.args.get("status")) in STATUSES:
            stmt = stmt.filter_by(status=status)
        ctx["rows"] = db.paginate(stmt, per_page=50)
    else:
        ctx["settings"] = {k: get_setting(k) for k in DEFAULT_SETTINGS}
    return render_template("admin.html", **ctx)


@bp.post("/toggle/<kind>/<int:obj_id>")
@role_required("admin")
def toggle(kind, obj_id):
    model = MODELS.get(kind) or abort(404)
    obj = db.get_or_404(model, obj_id)
    if kind == "user" and obj.id == current_user.id:
        flash("You can't deactivate yourself.", "error")
    else:
        obj.active = not obj.active
        db.session.commit()
        flash(f"{kind.capitalize()} #{obj.id} {'activated' if obj.active else 'deactivated'}.", "ok")
    return redirect(request.referrer if request.referrer and request.referrer.startswith(request.host_url) else url_for("admin.index"))


@bp.post("/users/<int:user_id>/role")
@role_required("admin")
def set_role(user_id):
    user = db.get_or_404(User, user_id)
    role = request.form.get("role")
    if role not in ROLES or user.id == current_user.id:
        abort(400)
    user.role = role
    db.session.commit()
    flash(f"{user.email} is now {role}.", "ok")
    return redirect(url_for("admin.index", tab="users"))


@bp.post("/settings")
@role_required("admin")
def settings():
    for key in DEFAULT_SETTINGS:
        value = request.form.get(key, "").strip()[:200]
        if key.endswith("_pct"):
            try:
                if not 0 <= float(value) <= 100:
                    raise ValueError
            except ValueError:
                flash(f"{key} must be a number from 0 to 100.", "error")
                return redirect(url_for("admin.index", tab="settings"))
        if key == "chatbot_enabled":
            value = "1" if value == "1" else "0"
        if not value:
            continue
        db.session.merge(Setting(key=key, value=value))
    db.session.commit()
    flash("Settings saved.", "ok")
    return redirect(url_for("admin.index", tab="settings"))
