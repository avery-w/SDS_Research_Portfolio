"""Seller area: store profile, products, inventory, images, fulfilment and sales analytics."""
import re
from datetime import date, timedelta

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from sqlalchemy import func

from core import Form, require, save_upload
from models import CATEGORIES, ITEM_STATUSES, REVENUE_STATUSES, Order, OrderItem, Product, Store, db, now, setting

bp = Blueprint("seller", __name__, url_prefix="/seller")


# ---------- analytics shared with the admin dashboard ----------

def revenue_by_day(*filters, days=30):
    """[(date, cents)] for the last `days` days, zero-filled so charts have no gaps."""
    start = date.today() - timedelta(days=days - 1)
    day = func.date(Order.created_at)
    rows = (db.session.query(day, func.sum(OrderItem.unit_price_cents * OrderItem.qty)).select_from(OrderItem)
            .join(Order).filter(Order.created_at >= start, OrderItem.status.in_(REVENUE_STATUSES), *filters)
            .group_by(day).all())
    rows = {str(k): v for k, v in rows}  # SQLite returns 'YYYY-MM-DD' strings, Postgres returns dates
    return [(d, int(rows.get(d.isoformat(), 0) or 0)) for d in (start + timedelta(i) for i in range(days))]


def top_products(*filters, limit=5):
    rev = func.sum(OrderItem.unit_price_cents * OrderItem.qty)
    return (db.session.query(OrderItem.name, func.sum(OrderItem.qty), rev)
            .filter(OrderItem.status.in_(REVENUE_STATUSES), *filters)
            .group_by(OrderItem.product_id, OrderItem.name).order_by(rev.desc()).limit(limit).all())


# ---------- store ----------

def my_store():
    """The seller's store. Sellers without one are sent to set it up."""
    s = g.user.store
    if not s:
        abort(409, "Set up your store first at /seller/store.")
    return s


def writable_store():
    s = my_store()
    if not s.is_active:
        abort(403, "Your store is suspended by the platform. Contact support to reinstate it.")
    return s


def slugify(name, store_id=None):
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "store"
    slug, n = base, 2
    while Store.query.filter(Store.slug == slug, Store.id != store_id).first():
        slug, n = f"{base}-{n}", n + 1
    return slug


@bp.get("")
@require("seller")
def dashboard():
    s = g.user.store
    if not s:
        return redirect(url_for("seller.store"))
    mine = OrderItem.store_id == s.id
    series = revenue_by_day(mine)
    stats = db.session.query(func.count(func.distinct(OrderItem.order_id)), func.coalesce(func.sum(OrderItem.qty), 0),
                             func.coalesce(func.sum(OrderItem.unit_price_cents * OrderItem.qty), 0)).filter(
        mine, OrderItem.status.in_(REVENUE_STATUSES)).one()
    commission = setting("commission_pct")
    return render_template(
        "seller/dashboard.html", s=s, series=series, orders=stats[0], units=stats[1], gross=stats[2],
        net=round(stats[2] * (1 - commission / 100)), commission=commission,
        to_ship=OrderItem.query.filter(mine, OrderItem.status == "pending").count(),
        returns=OrderItem.query.filter(mine, OrderItem.status == "return_requested").count(),
        low_stock=Product.query.filter(Product.store_id == s.id, Product.is_active, Product.stock <= 5)
        .order_by(Product.stock).all(),
        top=top_products(mine))


@bp.route("/store", methods=["GET", "POST"])
@require("seller")
def store():
    s = g.user.store
    if request.method == "POST":
        if s and not s.is_active:
            abort(403, "Your store is suspended by the platform. Contact support to reinstate it.")
        f = Form(request.form)
        name = f.str("name", "Store name", max_len=80, min_len=2)
        tagline = f.str("tagline", "Tagline", required=False, max_len=140)
        desc = f.str("description", "Description", required=False, max_len=4000)
        f.done()
        if not s:
            s = Store(owner_id=g.user.id)
            db.session.add(s)
        s.name, s.tagline, s.description = name, tagline, desc
        s.slug = slugify(name, s.id)
        db.session.commit()
        flash("Store saved.", "success")
        return redirect(url_for("seller.dashboard"))
    return render_template("seller/store.html", s=s)


# ---------- products & inventory ----------

def my_product(pid):
    p = db.session.get(Product, pid)
    if not p or p.store_id != my_store().id:
        abort(404)
    return p


@bp.get("/products")
@require("seller")
def products():
    s = my_store()
    return render_template("seller/products.html", s=s,
                           products=Product.query.filter_by(store_id=s.id).order_by(Product.id.desc()).all())


def fill_product(p, form, files):
    f = Form(form)
    p.name = f.str("name", "Product name", max_len=120, min_len=2)
    p.description = f.str("description", "Description", required=False, max_len=5000)
    p.category = f.choice("category", CATEGORIES, "Category")
    p.price_cents = f.money("price", "Price", lo=0.5, hi=50000)
    p.stock = f.int("stock", "Stock", lo=0, hi=100000)
    p.weight_lb = float(f.number("weight_lb", "Weight (lb)", lo=0.05, hi=150) or 1)
    for dim in ("length_in", "width_in", "height_in"):
        setattr(p, dim, float(f.number(dim, dim.split("_")[0].capitalize() + " (in)", lo=0.5, hi=108) or 1))
    f.done()
    upload = files.get("image")
    if upload and upload.filename:
        p.image = save_upload(upload)


@bp.route("/products/new", methods=["GET", "POST"])
@require("seller")
def new_product():
    s = writable_store() if request.method == "POST" else my_store()
    p = Product(store_id=s.id)
    if request.method == "POST":
        fill_product(p, request.form, request.files)
        db.session.add(p)
        db.session.commit()
        flash(f"\"{p.name}\" is live.", "success")
        return redirect(url_for("seller.products"))
    return render_template("seller/product_form.html", p=None)


@bp.route("/products/<int:pid>/edit", methods=["GET", "POST"])
@require("seller")
def edit_product(pid):
    p = my_product(pid)
    if request.method == "POST":
        writable_store()
        fill_product(p, request.form, request.files)
        db.session.commit()
        flash("Product updated.", "success")
        return redirect(url_for("seller.products"))
    return render_template("seller/product_form.html", p=p)


@bp.post("/products/<int:pid>/stock")
@require("seller")
def set_stock(pid):
    p = my_product(pid)
    writable_store()
    f = Form(request.form)
    p.stock = f.int("stock", "Stock", lo=0, hi=100000)
    f.done()
    db.session.commit()
    flash(f"{p.name}: stock set to {p.stock}.", "success")
    return redirect(url_for("seller.products"))


@bp.post("/products/<int:pid>/toggle")
@require("seller")
def toggle_product(pid):
    p = my_product(pid)
    writable_store()
    if p.locked:
        abort(403, "This listing was removed by a platform admin and can't be re-listed. Contact support.")
    p.is_active = not p.is_active
    db.session.commit()
    flash(f"{p.name} is now {'listed' if p.is_active else 'unlisted'}.", "success")
    return redirect(url_for("seller.products"))


# ---------- orders ----------

@bp.get("/orders")
@require("seller")
def orders():
    s = my_store()
    status = request.args.get("status")
    q = OrderItem.query.filter_by(store_id=s.id)
    if status in ITEM_STATUSES:
        q = q.filter_by(status=status)
    return render_template("seller/orders.html", items=q.order_by(OrderItem.id.desc()).limit(300).all(),
                           status=status, statuses=ITEM_STATUSES, today=now())
