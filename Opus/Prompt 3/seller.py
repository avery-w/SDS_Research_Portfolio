import io
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, select

from auth import clean, role_required
from models import REVENUE_STATUSES, Order, Product, Store, db

bp = Blueprint("seller", __name__, url_prefix="/seller")
IMAGE_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}


def number(name, lo, hi, cast=float):
    label = name.replace("_", " ").capitalize()
    try:
        value = cast(request.form.get(name, ""))
        in_range = lo <= value <= hi  # False for NaN/inf floats, InvalidOperation for Decimal NaN
    except (ValueError, InvalidOperation):
        raise ValueError(f"{label} must be a number.")
    if not in_range:
        raise ValueError(f"{label} must be between {lo} and {hi}.")
    return value


def save_image(upload):
    """Validates the bytes with Pillow and stores under a random name. The client filename is never used."""
    data = upload.read()
    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt = img.format
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
        raise ValueError("Upload a valid JPEG, PNG, WEBP or GIF image.")
    if fmt not in IMAGE_FORMATS:
        raise ValueError("Upload a valid JPEG, PNG, WEBP or GIF image.")
    name = f"{uuid.uuid4().hex}.{IMAGE_FORMATS[fmt]}"
    (Path(current_app.config["UPLOAD_DIR"]) / name).write_bytes(data)
    return name


def my_store():
    return current_user.store


@bp.route("/", methods=["GET", "POST"])
@role_required("seller")
def dashboard():
    store = my_store()
    if request.method == "POST":  # create or edit store
        try:
            name, desc = clean("name", 100), clean("description", 2000, required=False)
            clash = db.session.scalar(select(Store).where(func.lower(Store.name) == name.lower()))
            if clash and clash is not store:
                raise ValueError("That store name is taken.")
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("seller.dashboard"))
        if store:
            store.name, store.description = name, desc
        else:
            db.session.add(Store(owner_id=current_user.id, name=name, description=desc))
        db.session.commit()
        flash("Store saved.", "ok")
        return redirect(url_for("seller.dashboard"))
    if not store:
        return render_template("seller.html", store=None)
    products = db.session.scalars(select(Product).filter_by(store_id=store.id).order_by(Product.name)).all()
    orders = db.session.scalars(select(Order).filter_by(store_id=store.id).order_by(Order.created_at.desc()).limit(100)).all()
    sales = db.session.execute(
        select(func.count(Order.id), func.coalesce(func.sum(Order.subtotal_cents), 0))
        .where(Order.store_id == store.id, Order.status.in_(REVENUE_STATUSES))
    ).one()
    return render_template("seller.html", store=store, products=products, orders=orders, sales=sales)


@bp.route("/products/new", methods=["GET", "POST"], defaults={"product_id": None})
@bp.route("/products/<int:product_id>", methods=["GET", "POST"])
@role_required("seller", "admin")
def product_form(product_id):
    if product_id:
        p = db.get_or_404(Product, product_id)
        if current_user.role != "admin" and p.store_id != getattr(my_store(), "id", None):
            abort(404)
    else:
        if not my_store():
            flash("Create your store first.", "error")
            return redirect(url_for("seller.dashboard"))
        p = None
    if request.method == "POST":
        try:
            fields = dict(
                name=clean("name", 150),
                description=clean("description", 5000, required=False),
                price_cents=int((number("price", Decimal("0"), Decimal("1000000"), Decimal) * 100).to_integral_value()),
                stock=number("stock", 0, 100000, int),
                weight_lb=number("weight_lb", 0.01, 150),
                length_in=number("length_in", 0.1, 108),
                width_in=number("width_in", 0.1, 108),
                height_in=number("height_in", 0.1, 108),
                active=request.form.get("active") == "on",
            )
            upload = request.files.get("image")
            if upload and upload.filename:
                fields["image"] = save_image(upload)
        except ValueError as e:
            flash(str(e), "error")
            return render_template("product_form.html", p=p), 400
        if p is None:
            p = Product(store_id=my_store().id)
            db.session.add(p)
        for k, v in fields.items():
            setattr(p, k, v)
        db.session.commit()
        flash("Product saved.", "ok")
        return redirect(url_for("admin.index", tab="products") if current_user.role == "admin" else url_for("seller.dashboard"))
    return render_template("product_form.html", p=p)
