import os
import uuid

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from . import to_cents
from .auth import role_required
from .models import ORDER_STATUSES, SELLER_TRANSITIONS, Order, Product, Store, db, sales_summary

bp = Blueprint("seller", __name__, url_prefix="/seller")
IMAGE_SIGNATURES = {b"\x89PNG\r\n\x1a\n": ".png", b"\xff\xd8\xff": ".jpg", b"GIF87a": ".gif", b"GIF89a": ".gif"}


def save_image(file):
    """Validate an upload by its file signature (not its name) and store it under a random name."""
    head = file.stream.read(12)
    file.stream.seek(0)
    ext = next((e for sig, e in IMAGE_SIGNATURES.items() if head.startswith(sig)), None)
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        ext = ".webp"
    if not ext:
        raise ValueError("Images must be PNG, JPEG, GIF or WebP.")
    name = uuid.uuid4().hex + ext
    file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], name))
    return name


def number(form, key, cast=float):
    try:
        return cast(form.get(key, ""))
    except ValueError:
        raise ValueError(f"{key.split('_')[0].capitalize()} must be a number.") from None


def my_store():
    """The seller's active store, or redirect them to set one up."""
    store = current_user.store
    if not store:
        abort(redirect(url_for("seller.dashboard")))
    if not store.active:
        flash("Your store has been deactivated by an administrator.", "error")
        abort(redirect(url_for("seller.dashboard")))
    return store


@bp.route("/", methods=["GET", "POST"])
@role_required("seller")
def dashboard():
    store = current_user.store
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        taken = db.session.scalar(select(Store).where(Store.name == name, Store.id != (store.id if store else 0)))
        if not name or taken:
            flash("Store name is required and must be unique.", "error")
        else:
            if not store:
                store = Store(owner_id=current_user.id)
                db.session.add(store)
            store.name = name
            store.description = request.form.get("description", "").strip()
            db.session.commit()
            flash("Store saved.", "success")
        return redirect(url_for("seller.dashboard"))
    stats = sales_summary(store.id) if store else None
    low_stock = [p for p in store.products if p.active and p.stock <= 5] if store else []
    return render_template("seller/dashboard.html", store=store, stats=stats, low_stock=low_stock)


@bp.route("/products")
@role_required("seller")
def products():
    store = my_store()
    rows = db.session.scalars(select(Product).filter_by(store_id=store.id).order_by(Product.created_at.desc()))
    return render_template("seller/products.html", products=list(rows))


@bp.route("/products/new", methods=["GET", "POST"])
@bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@role_required("seller", "admin")
def product_form(product_id=None):
    if product_id:
        p = db.get_or_404(Product, product_id)
        if current_user.role != "admin" and p.store_id != my_store().id:
            abort(404)
    elif current_user.role == "admin":
        abort(403)  # admins manage existing products; listings belong to a seller's store
    else:
        p = Product(store_id=my_store().id)

    if request.method == "POST":
        f = request.form
        try:
            p.name = f.get("name", "").strip()
            if not p.name:
                raise ValueError("Name is required.")
            p.description = f.get("description", "").strip()
            p.category = f.get("category", "").strip() or "General"
            p.price_cents = to_cents(f.get("price", ""))
            p.stock = number(f, "stock", int)
            p.weight_lb, p.length_in, p.width_in, p.height_in = (
                number(f, k) for k in ("weight_lb", "length_in", "width_in", "height_in")
            )
            if p.stock < 0 or min(p.weight_lb, p.length_in, p.width_in, p.height_in) <= 0:
                raise ValueError("Stock can't be negative and weight/dimensions must be positive.")
            p.active = bool(f.get("active"))
            if image := request.files.get("image"):
                if image.filename:
                    p.image = save_image(image)
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
            return render_template("seller/product_form.html", p=p, form=f), 400
        if not p.id:
            db.session.add(p)
        db.session.commit()
        flash("Product saved.", "success")
        return redirect(url_for("admin.products") if current_user.role == "admin" else url_for("seller.products"))
    return render_template("seller/product_form.html", p=p, form=None)


@bp.route("/orders")
@role_required("seller")
def orders():
    store = my_store()
    status = request.args.get("status", "")
    stmt = select(Order).filter_by(store_id=store.id).order_by(Order.created_at.desc())
    if status in ORDER_STATUSES:
        stmt = stmt.filter_by(status=status)
    return render_template("orders.html", orders=list(db.session.scalars(stmt)), title="Store orders", status=status, statuses=ORDER_STATUSES)


@bp.route("/orders/<int:order_id>", methods=["POST"])
@role_required("seller")
def order_update(order_id):
    o = db.get_or_404(Order, order_id)
    if o.store_id != my_store().id:
        abort(404)
    status = request.form.get("status", "")
    if status not in SELLER_TRANSITIONS.get(o.status, ()):
        flash("That change isn't allowed for this order.", "error")
    elif status == "shipped" and not request.form.get("tracking_number", "").strip():
        flash("Enter the UPS tracking number.", "error")
    else:
        if status == "shipped":
            o.tracking_number = request.form["tracking_number"].strip()[:60]
        o.set_status(status)
        db.session.commit()
        flash(f"Order #{o.id} marked {status.replace('_', ' ')}.", "success")
    return redirect(url_for("shop.order", order_id=o.id))
