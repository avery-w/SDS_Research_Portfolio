from itertools import groupby

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import case, func, or_, select, update

import shipping
from auth import clean, clean_address, role_required
from models import Message, Order, OrderItem, Product, Store, User, db, get_setting

bp = Blueprint("shop", __name__)
SORTS = {"new": Product.created_at.desc(), "price_asc": Product.price_cents, "price_desc": Product.price_cents.desc()}
MAX_QTY = 99


def visible_products():
    return select(Product).join(Store).join(User, Store.owner_id == User.id).where(Product.active, Store.active, User.active)


def get_visible(product_id):
    return db.session.scalar(visible_products().where(Product.id == product_id)) or abort(404)


@bp.get("/")
def index():
    stmt = visible_products()
    q = request.args.get("q", "").strip()[:100]
    if q:
        needle = q.lower()
        stmt = stmt.where(or_(func.lower(Product.name).contains(needle, autoescape=True),
                              func.lower(Product.description).contains(needle, autoescape=True)))
    store = None
    if store_id := request.args.get("store", type=int):
        store = db.session.get(Store, store_id)
        if not store or not store.active:
            abort(404)
        stmt = stmt.where(Product.store_id == store_id)
    sort = request.args.get("sort", "new")
    stmt = stmt.order_by(SORTS.get(sort, SORTS["new"]))
    page = db.paginate(stmt, per_page=24, max_per_page=24)
    return render_template("index.html", page=page, q=q, sort=sort, store=store)


@bp.get("/product/<int:product_id>")
def product(product_id):
    return render_template("product.html", p=get_visible(product_id))


# ---------- cart (kept in the signed session cookie: {product_id: qty}) ----------

def cart_lines():
    cart = session.get("cart", {})
    if not cart:
        return []
    ids = [int(pid) for pid in cart]
    products = db.session.scalars(visible_products().where(Product.id.in_(ids)).order_by(Product.store_id)).all()
    return [(p, cart[str(p.id)]) for p in products]


def rates_by_store(lines, dest_zip):
    """{store_id: {service: cents}}. Each unit ships as its own UPS package from the Austin origin."""
    zone = shipping.zone_for_zip(dest_zip)
    fuel = float(get_setting("fuel_surcharge_pct"))
    return {
        store_id: shipping.quote_packages([p.package for p, qty in group for _ in range(qty)], zone, fuel)
        for store_id, group in ((sid, list(g)) for sid, g in groupby(lines, key=lambda line: line[0].store_id))
    }


@bp.post("/cart/add/<int:product_id>")
def cart_add(product_id):
    p = get_visible(product_id)
    cart = session.setdefault("cart", {})
    qty = min(cart.get(str(p.id), 0) + max(request.form.get("qty", 1, type=int), 1), MAX_QTY, p.stock)
    if qty <= 0:
        flash("Out of stock.", "error")
    else:
        cart[str(p.id)] = qty
        session.modified = True
        flash(f"Added {p.name} to cart.", "ok")
    return redirect(url_for("shop.product", product_id=p.id))


@bp.post("/cart/update/<int:product_id>")
def cart_update(product_id):
    cart = session.get("cart", {})
    qty = request.form.get("qty", 0, type=int)
    if qty <= 0:
        cart.pop(str(product_id), None)
    else:
        cart[str(product_id)] = min(qty, MAX_QTY)
    session.modified = True
    return redirect(url_for("shop.cart"))


@bp.get("/cart")
def cart():
    lines = cart_lines()
    subtotal = sum(p.price_cents * q for p, q in lines)
    return render_template("cart.html", lines=lines, subtotal=subtotal, services=shipping.SERVICES, origin=shipping.ORIGIN)


@bp.post("/api/checkout/rates")
def api_rates():
    """JSON: {"zip": "10001"} -> UPS rates for every service, summed across the stores in the cart."""
    data = request.get_json(silent=True) or {}
    lines = cart_lines()
    if not lines:
        return jsonify(error="Cart is empty."), 400
    try:
        per_store = rates_by_store(lines, str(data.get("zip", "")))
    except ValueError as e:
        return jsonify(error=str(e)), 400
    subtotal = sum(p.price_cents * q for p, q in lines)
    return jsonify(
        origin=shipping.ORIGIN,
        subtotal_cents=subtotal,
        rates=[{"service": code, "name": name, "cents": sum(r[code] for r in per_store.values()),
                "total_cents": subtotal + sum(r[code] for r in per_store.values())}
               for code, (name, _) in shipping.SERVICES.items()],
    )


@bp.post("/checkout")
@role_required("customer")
def checkout():
    lines = cart_lines()
    service = request.form.get("service", "")
    try:
        if not lines:
            raise ValueError("Cart is empty.")
        if service not in shipping.SERVICES:
            raise ValueError("Choose a shipping service.")
        name = clean("name", 100)
        street, city, state, zip_code = clean_address()
        per_store = rates_by_store(lines, zip_code)  # prices and shipping always recomputed server side
        orders = []
        for store_id, group in groupby(lines, key=lambda line: line[0].store_id):
            group = list(group)
            subtotal = sum(p.price_cents * q for p, q in group)
            ship = per_store[store_id][service]
            order = Order(customer_id=current_user.id, store_id=store_id, subtotal_cents=subtotal,
                          shipping_cents=ship, total_cents=subtotal + ship, ship_service=service,
                          ship_name=name, ship_street=street, ship_city=city, ship_state=state, ship_zip=zip_code)
            db.session.add(order)
            for p, qty in group:
                # Atomic decrement, so two buyers can never both take the last unit.
                taken = db.session.execute(
                    update(Product).where(Product.id == p.id, Product.stock >= qty).values(stock=Product.stock - qty)
                ).rowcount
                if not taken:
                    raise ValueError(f"Only {p.stock} of {p.name} left in stock.")
                order.items.append(OrderItem(product_id=p.id, name=p.name, price_cents=p.price_cents, quantity=qty))
            orders.append(order)
        # ponytail: no payment processor yet. Charge here (e.g. Stripe PaymentIntent) before commit, before going live.
        db.session.commit()
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "error")
        return redirect(url_for("shop.cart"))
    session.pop("cart", None)
    flash(f"Placed {len(orders)} order(s). Sellers ship separately.", "ok")
    return redirect(url_for("shop.orders"))


# ---------- orders (shared by customer, seller and admin) ----------

@bp.get("/orders")
@login_required
def orders():
    rows = db.session.scalars(select(Order).filter_by(customer_id=current_user.id).order_by(Order.created_at.desc())).all()
    return render_template("orders.html", orders=rows)


def order_role(order):
    if current_user.role == "admin":
        return "admin"
    if order.store.owner_id == current_user.id:
        return "seller"
    if order.customer_id == current_user.id:
        return "customer"
    abort(404)  # 404 rather than 403 so order ids can't be probed


@bp.get("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = db.get_or_404(Order, order_id)
    role = order_role(order)
    return render_template("order.html", o=order, role=role, allowed=sorted(order.allowed_statuses(role)))


@bp.post("/orders/<int:order_id>/status")
@login_required
def order_status(order_id):
    order = db.get_or_404(Order, order_id)
    role = order_role(order)
    new = request.form.get("status", "")
    try:
        if new == "shipped":
            order.tracking = clean("tracking", 40, required=role != "admin")
            if order.tracking and not order.tracking.isalnum():
                raise ValueError("Tracking number must be letters and digits only.")
        if new == "return_requested":
            order.return_reason = clean("return_reason", 1000)
        order.change_status(new, role)
        db.session.commit()
        flash(f"Order #{order.id} is now {new.replace('_', ' ')}.", "ok")
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "error")
    return redirect(url_for("shop.order_detail", order_id=order.id))


# ---------- customer <-> seller messaging ----------

def can_message(other):
    if not other or not other.active or other.id == current_user.id:
        return False
    if other.role in ("seller", "admin") or current_user.role == "admin":
        return True
    # Sellers can reply to anyone who wrote to them first; customers can't cold message each other.
    return db.session.scalar(select(Message.id).filter_by(sender_id=other.id, recipient_id=current_user.id).limit(1)) is not None


@bp.get("/messages")
@login_required
def inbox():
    me = current_user.id
    other = case((Message.sender_id == me, Message.recipient_id), else_=Message.sender_id)
    rows = db.session.execute(
        select(other.label("uid"), func.max(Message.created_at).label("last"),
               func.sum(case(((Message.recipient_id == me) & Message.read.is_(False), 1), else_=0)).label("unread"))
        .where(or_(Message.sender_id == me, Message.recipient_id == me))
        .group_by("uid").order_by(func.max(Message.created_at).desc())
    ).all()
    users = {u.id: u for u in db.session.scalars(select(User).where(User.id.in_([r.uid for r in rows])))}
    return render_template("messages.html", threads=[(users[r.uid], r.last, r.unread) for r in rows])


@bp.route("/messages/<int:user_id>", methods=["GET", "POST"])
@login_required
def thread(user_id):
    other = db.get_or_404(User, user_id)
    me = current_user.id
    product = get_visible(pid) if (pid := request.values.get("product", type=int)) else None
    order = db.session.get(Order, oid) if (oid := request.values.get("order", type=int)) else None
    if order:
        order_role(order)  # must be a party to the order to reference it
    if request.method == "POST":
        if not can_message(other):
            abort(403)
        try:
            body = clean("body", 2000)
        except ValueError as e:
            flash(str(e), "error")
        else:
            db.session.add(Message(sender_id=me, recipient_id=other.id, body=body,
                                   product_id=product.id if product else None, order_id=order.id if order else None))
            db.session.commit()
        return redirect(url_for("shop.thread", user_id=other.id))
    msgs = db.session.scalars(select(Message).where(or_(
        (Message.sender_id == me) & (Message.recipient_id == other.id),
        (Message.sender_id == other.id) & (Message.recipient_id == me),
    )).order_by(Message.created_at)).all()
    if not msgs and not can_message(other):
        abort(404)
    db.session.execute(update(Message).where(Message.sender_id == other.id, Message.recipient_id == me).values(read=True))
    db.session.commit()
    return render_template("thread.html", other=other, msgs=msgs, product=product, order=order, can_reply=can_message(other))
