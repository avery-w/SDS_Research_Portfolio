from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_, select

from .models import CUSTOMER_TRANSITIONS, ORDER_STATUSES, SELLER_TRANSITIONS, CartItem, Message, Order, Product, Store, User, db

bp = Blueprint("shop", __name__)
SORTS = {
    "new": Product.created_at.desc(),
    "price_asc": Product.price_cents.asc(),
    "price_desc": Product.price_cents.desc(),
    "name": Product.name.asc(),
}


def visible_products():
    """Products customers may see and buy: active product, active store, active seller."""
    return (
        select(Product)
        .join(Store)
        .join(User, Store.owner_id == User.id)
        .where(Product.active, Store.active, User.active)
    )


def cart_by_store(user):
    """{store: [(product, qty)]} for purchasable lines in the user's cart."""
    groups = {}
    for item in db.session.scalars(select(CartItem).filter_by(user_id=user.id)):
        p = item.product
        if p.active and p.store.active and p.store.owner.active:
            groups.setdefault(p.store, []).append((p, item.quantity))
    return groups


def search_products(q="", category="", limit=None):
    stmt = visible_products()
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Product.name.ilike(like), Product.description.ilike(like), Product.category.ilike(like)))
    if category:
        stmt = stmt.where(Product.category == category)
    return stmt.limit(limit) if limit else stmt


@bp.route("/")
def index():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "")
    sort = request.args.get("sort", "new")
    stmt = search_products(q, category).order_by(SORTS.get(sort, SORTS["new"]))
    if (low := request.args.get("min", type=float)) is not None:
        stmt = stmt.where(Product.price_cents >= int(low * 100))
    if (high := request.args.get("max", type=float)) is not None:
        stmt = stmt.where(Product.price_cents <= int(high * 100))
    page = db.paginate(stmt, per_page=24, error_out=False)
    categories = db.session.scalars(visible_products().with_only_columns(Product.category).distinct().order_by(Product.category))
    return render_template("index.html", page=page, q=q, category=category, sort=sort, categories=list(categories))


@bp.route("/product/<int:product_id>")
def product(product_id):
    p = db.session.scalar(visible_products().where(Product.id == product_id)) or abort(404)
    return render_template("product.html", p=p)


@bp.route("/store/<int:store_id>")
def store(store_id):
    s = db.get_or_404(Store, store_id)
    if not s.active:
        abort(404)
    products = db.session.scalars(visible_products().where(Product.store_id == s.id).order_by(Product.created_at.desc()))
    return render_template("store.html", store=s, products=list(products))


@bp.route("/cart")
@login_required
def cart():
    groups = cart_by_store(current_user)
    subtotal = sum(p.price_cents * qty for lines in groups.values() for p, qty in lines)
    return render_template("cart.html", groups=groups, subtotal=subtotal)


@bp.route("/cart/<int:product_id>", methods=["POST"])
@login_required
def cart_set(product_id):
    """Add (mode=add) or set the quantity of a cart line; quantity 0 removes it."""
    p = db.session.scalar(visible_products().where(Product.id == product_id)) or abort(404)
    try:
        qty = int(request.form.get("quantity", 1))
    except ValueError:
        abort(400)
    item = db.session.scalar(select(CartItem).filter_by(user_id=current_user.id, product_id=p.id))
    if request.form.get("mode") == "add":
        qty += item.quantity if item else 0
    qty = min(qty, p.stock)
    if qty <= 0:
        if item:
            db.session.delete(item)
        if p.stock == 0:
            flash(f"{p.name} is out of stock.", "error")
    elif item:
        item.quantity = qty
    else:
        db.session.add(CartItem(user_id=current_user.id, product_id=p.id, quantity=qty))
    db.session.commit()
    if request.form.get("mode") == "add" and qty > 0:
        flash(f"Added {p.name} to your cart.", "success")
    if request.form.get("back") == "product":
        return redirect(url_for("shop.product", product_id=p.id))
    return redirect(url_for("shop.cart"))


@bp.route("/checkout")
@login_required
def checkout():
    groups = cart_by_store(current_user)
    if not groups:
        flash("Your cart is empty.", "error")
        return redirect(url_for("shop.cart"))
    subtotal = sum(p.price_cents * qty for lines in groups.values() for p, qty in lines)
    return render_template("checkout.html", groups=groups, subtotal=subtotal)


@bp.route("/orders")
@login_required
def orders():
    rows = db.session.scalars(select(Order).filter_by(customer_id=current_user.id).order_by(Order.created_at.desc()))
    return render_template("orders.html", orders=list(rows), title="My orders")


def can_view_order(order):
    return (
        current_user.role == "admin"
        or order.customer_id == current_user.id
        or (current_user.store and order.store_id == current_user.store.id)
    )


@bp.route("/orders/<int:order_id>")
@login_required
def order(order_id):
    o = db.get_or_404(Order, order_id)
    if not can_view_order(o):
        abort(404)
    return render_template("order.html", o=o, seller_next=SELLER_TRANSITIONS.get(o.status, ()), statuses=ORDER_STATUSES)


@bp.route("/orders/<int:order_id>/<action>", methods=["POST"])
@login_required
def order_action(order_id, action):
    o = db.get_or_404(Order, order_id)
    if o.customer_id != current_user.id:
        abort(404)
    status = {"cancel": "cancelled", "return": "return_requested"}.get(action) or abort(404)
    if status not in CUSTOMER_TRANSITIONS.get(o.status, ()):
        flash(f"This order can't be {'cancelled' if action == 'cancel' else 'returned'} now.", "error")
    elif action == "return" and not request.form.get("reason", "").strip():
        flash("Tell the seller why you're returning the order.", "error")
    else:
        o.return_reason = request.form.get("reason", "").strip()[:2000]
        o.set_status(status)
        db.session.commit()
        flash("Order cancelled." if action == "cancel" else "Return requested. The seller will review it.", "success")
    return redirect(url_for("shop.order", order_id=o.id))


@bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    if request.method == "POST":
        f = request.form
        u = current_user
        u.name = f.get("name", u.name).strip() or u.name
        u.street, u.city = f.get("street", "").strip(), f.get("city", "").strip()
        u.state, u.zip = f.get("state", "").strip().upper()[:2], f.get("zip", "").strip()[:10]
        if f.get("new_password"):
            if not u.check_password(f.get("current_password", "")):
                flash("Current password is incorrect.", "error")
                return redirect(url_for("shop.account"))
            if len(f["new_password"]) < 8:
                flash("New password must be at least 8 characters.", "error")
                return redirect(url_for("shop.account"))
            u.set_password(f["new_password"])
        db.session.commit()
        flash("Account updated.", "success")
        return redirect(url_for("shop.account"))
    return render_template("account.html")


@bp.route("/messages")
@login_required
def inbox():
    msgs = db.session.scalars(
        select(Message)
        .where(or_(Message.sender_id == current_user.id, Message.recipient_id == current_user.id))
        .order_by(Message.created_at.desc())
    )
    threads = {}
    for m in msgs:  # newest message per conversation partner
        other = m.recipient if m.sender_id == current_user.id else m.sender
        if other.id not in threads:
            threads[other.id] = {"user": other, "last": m, "unread": 0}
        if m.recipient_id == current_user.id and not m.read:
            threads[other.id]["unread"] += 1
    return render_template("messages.html", threads=threads.values())


@bp.route("/messages/<int:user_id>", methods=["GET", "POST"])
@login_required
def thread(user_id):
    other = db.get_or_404(User, user_id)
    if other.id == current_user.id:
        abort(404)
    # Customers may start conversations with sellers and admins; anyone may reply to an existing thread.
    existing = db.session.scalar(select(Message.id).where(Message.sender_id == other.id, Message.recipient_id == current_user.id).limit(1))
    if current_user.role == "customer" and other.role == "customer" and not existing:
        abort(403)
    product_id = request.values.get("product", type=int)
    order_id = request.values.get("order", type=int)
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        if not body:
            flash("Message can't be empty.", "error")
        elif not other.active:
            flash("This account is no longer active.", "error")
        else:
            product = db.session.get(Product, product_id) if product_id else None
            order = db.session.get(Order, order_id) if order_id else None
            db.session.add(
                Message(
                    sender_id=current_user.id,
                    recipient_id=other.id,
                    body=body[:5000],
                    product_id=product.id if product else None,
                    order_id=order.id if order and can_view_order(order) else None,
                )
            )
            db.session.commit()
        return redirect(url_for("shop.thread", user_id=other.id))
    msgs = list(
        db.session.scalars(
            select(Message)
            .where(
                or_(
                    (Message.sender_id == current_user.id) & (Message.recipient_id == other.id),
                    (Message.sender_id == other.id) & (Message.recipient_id == current_user.id),
                )
            )
            .order_by(Message.created_at)
        )
    )
    for m in msgs:
        if m.recipient_id == current_user.id:
            m.read = True
    db.session.commit()
    context_product = db.session.get(Product, product_id) if product_id else None
    return render_template("thread.html", other=other, msgs=msgs, product=context_product, order_id=order_id)
