"""Public catalog, auth, customer account/cart/checkout/orders, and customer<->seller messaging."""
import secrets
from datetime import timedelta

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy import func, or_

from core import (Form, Invalid, audit, cart_lines, login_user, rate_limit, require, safe_next,
                  set_item_status, shipping_quote, take_stock)
from models import (CATEGORIES, CartItem, Conversation, Message, Order, OrderItem, Product, Store, User,
                    db, now, setting)
import shipping

bp = Blueprint("shop", __name__)
SORTS = {"new": Product.created_at.desc(), "price_asc": Product.price_cents.asc(),
         "price_desc": Product.price_cents.desc(), "name": Product.name.asc()}


# ---------- catalog ----------

def catalog(q="", category=None, min_cents=None, max_cents=None, sort="new", store_id=None):
    """Products a customer may see and buy: active product, active store, active seller."""
    query = Product.query.join(Store).join(User, Store.owner_id == User.id).filter(
        Product.is_active, Store.is_active, User.is_active)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Product.name.ilike(like), Product.description.ilike(like),
                                 Product.category.ilike(like), Store.name.ilike(like)))
    if category:
        query = query.filter(Product.category == category)
    if min_cents is not None:
        query = query.filter(Product.price_cents >= min_cents)
    if max_cents is not None:
        query = query.filter(Product.price_cents <= max_cents)
    if store_id:
        query = query.filter(Product.store_id == store_id)
    return query.order_by(SORTS.get(sort, SORTS["new"]))


def visible_product(pid):
    p = db.session.get(Product, pid)
    if not p or not p.purchasable:
        abort(404, "That product isn't available.")
    return p


@bp.get("/")
def home():
    return render_template("home.html", featured=catalog().limit(8).all(),
                           deals=catalog(sort="price_asc").filter(Product.stock > 0).limit(4).all())


@bp.get("/products")
def products():
    # Browsing is forgiving: unparseable filters fall back to defaults instead of erroring.
    a = request.args
    cat = a.get("category") if a.get("category") in CATEGORIES else None
    lo, hi = a.get("min", type=float), a.get("max", type=float)
    query = catalog(a.get("q", "").strip()[:100], cat, int(lo * 100) if lo else None,
                    int(hi * 100) if hi else None, a.get("sort", "new"))
    page = query.paginate(page=max(a.get("page", 1, type=int), 1), per_page=12, error_out=False)
    return render_template("products.html", page=page, store=None)


@bp.get("/products/<int:pid>")
def product(pid):
    p = visible_product(pid)
    related = catalog(category=p.category).filter(Product.id != p.id).limit(4).all()
    return render_template("product.html", p=p, related=related)


@bp.get("/stores/<slug>")
def store(slug):
    s = Store.query.filter_by(slug=slug).first()
    if not s or not s.is_active or not s.owner.is_active:
        abort(404, "That store isn't open.")
    page = catalog(store_id=s.id).paginate(page=max(request.args.get("page", 1, type=int), 1),
                       per_page=12, error_out=False)
    return render_template("products.html", page=page, store=s)


# ---------- auth ----------

@bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("shop.home"))
    if request.method == "POST":
        rate_limit("register", 10, 3600)
        f = Form(request.form)
        name, email = f.str("name", "Name", max_len=100), f.email()
        pw = f.str("password", "Password", min_len=8, max_len=128)
        roles = ["customer", "seller"] if setting("allow_seller_signup") else ["customer"]
        role = f.choice("role", roles, "Account type")
        if email and User.query.filter_by(email=email).first():
            f.errors["email"] = "An account with that email already exists."
        f.done()
        user = User(name=name, email=email, role=role)
        user.set_password(pw)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash(f"Welcome, {name}!", "success")
        return redirect(url_for("seller.store") if role == "seller" else url_for("shop.home"))
    return render_template("auth.html", mode="register")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        rate_limit("login", 10, 300)
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(request.form.get("password", "")):
            flash("Email or password is incorrect.", "error")
            return render_template("auth.html", mode="login"), 401
        if not user.is_active:
            flash("This account has been deactivated. Contact support@longhorn.market.", "error")
            return render_template("auth.html", mode="login"), 403
        login_user(user)
        home = {"seller": url_for("seller.dashboard"), "admin": url_for("admin.dashboard")}.get(user.role, "/")
        return redirect(safe_next(request.args.get("next"), home))
    return render_template("auth.html", mode="login")


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("shop.home"))


# ---------- account ----------

@bp.route("/account", methods=["GET", "POST"])
@require()
def account():
    u = g.user
    if request.method == "POST":
        f = Form(request.form)
        u.name = f.str("name", "Name", max_len=100)
        email = f.email()
        if email != u.email and User.query.filter_by(email=email).first():
            f.errors["email"] = "An account with that email already exists."
        if any(request.form.get(k) for k in ("street", "city", "state", "zip")):
            u.street = f.str("street", "Street", max_len=200, min_len=3)
            u.city = f.str("city", "City", max_len=100)
            u.state = f.state()
            u.zip = f.zip()
        f.done()
        u.email = email
        db.session.commit()
        flash("Profile saved.", "success")
        return redirect(url_for("shop.account"))
    return render_template("account.html")


@bp.post("/account/password")
@require()
def change_password():
    f = Form(request.form)
    new = f.str("new_password", "New password", min_len=8, max_len=128)
    if not g.user.check_password(request.form.get("current_password", "")):
        f.errors["current_password"] = "Current password is incorrect."
    f.done()
    g.user.set_password(new)
    db.session.commit()
    flash("Password updated.", "success")
    return redirect(url_for("shop.account"))


@bp.post("/account/deactivate")
@require("customer", "seller")
def deactivate_self():
    if not g.user.check_password(request.form.get("password", "")):
        raise Invalid({"password": "Enter your password to confirm."})
    g.user.is_active = False
    audit("user.self_deactivate", g.user.email)
    db.session.commit()
    session.clear()
    flash("Your account has been deactivated. We're sorry to see you go.", "info")
    return redirect(url_for("shop.home"))


# ---------- cart ----------

@bp.get("/cart")
@require("customer")
def cart():
    return render_template("cart.html", lines=cart_lines(g.user))


def add_to_cart(user, product_id, qty):
    """Shared by the HTML form and the JSON API. Sets (not adds) when the line exists and qty is absolute."""
    p = visible_product(product_id)
    line = CartItem.query.filter_by(user_id=user.id, product_id=p.id).first()
    total = qty + (line.qty if line else 0)
    if total > p.stock:
        abort(409, f"Only {p.stock} of \"{p.name}\" in stock.")
    if line:
        line.qty = total
    else:
        db.session.add(CartItem(user_id=user.id, product_id=p.id, qty=qty))
    db.session.commit()
    return p


def set_cart_qty(user, product_id, qty):
    line = CartItem.query.filter_by(user_id=user.id, product_id=product_id).first_or_404()
    if qty == 0:
        db.session.delete(line)
    elif qty > line.product.stock:
        abort(409, f"Only {line.product.stock} of \"{line.product.name}\" in stock.")
    else:
        line.qty = qty
    db.session.commit()


@bp.post("/cart/add")
@require("customer")
def cart_add():
    f = Form(request.form)
    pid, qty = f.int("product_id", "Product", lo=1), f.int("qty", "Quantity", lo=1, hi=99)
    f.done()
    p = add_to_cart(g.user, pid, qty)
    flash(f"Added {qty} x {p.name} to your cart.", "success")
    return redirect(url_for("shop.cart"))


@bp.post("/cart/<int:pid>")
@require("customer")
def cart_update(pid):
    f = Form(request.form)
    qty = f.int("qty", "Quantity", lo=0, hi=99)
    f.done()
    set_cart_qty(g.user, pid, qty)
    return redirect(url_for("shop.cart"))


# ---------- checkout ----------

def place_order(user, addr, service):
    """Shared by the checkout page and POST /api/checkout."""
    lines = cart_lines(user)
    if not lines:
        abort(409, "Your cart is empty.")
    gone = [c.product.name for c in lines if not c.product.purchasable]
    if gone:
        abort(409, f"No longer available: {', '.join(gone)}. Remove it from your cart to continue.")
    pairs = [(c.product, c.qty) for c in lines]
    quote = shipping_quote(addr["zip"], pairs)
    opt = next((o for o in quote["options"] if o["service"] == service), None)
    if not opt:
        raise Invalid({"service": "That UPS service isn't available for this address."})
    for c in lines:
        if not take_stock(c.product_id, c.qty):
            name = c.product.name
            db.session.rollback()
            abort(409, f"Sorry, \"{name}\" sold out while you were checking out. Update your cart and try again.")
    subtotal = sum(p.price_cents * q for p, q in pairs)
    tax = round(subtotal * setting("tax_rate_pct") / 100)
    ship = round(opt["total"] * 100)
    order = Order(user_id=user.id, subtotal_cents=subtotal, shipping_cents=ship, tax_cents=tax,
                  total_cents=subtotal + ship + tax, shipping_service=opt["name"],
                  **{f"ship_{k}": v for k, v in addr.items()})
    for c in lines:
        order.items.append(OrderItem(product_id=c.product_id, store_id=c.product.store_id, name=c.product.name,
                                     unit_price_cents=c.product.price_cents, qty=c.qty))
        db.session.delete(c)
    db.session.add(order)
    # ponytail: payment capture is simulated. Put the payment-intent call here, before commit.
    db.session.commit()
    return order


@bp.route("/checkout", methods=["GET", "POST"])
@require("customer")
def checkout():
    lines = cart_lines(g.user)
    if not lines:
        flash("Your cart is empty.", "info")
        return redirect(url_for("shop.cart"))
    if request.method == "POST":
        f = Form(request.form)
        addr = f.address()
        service = f.choice("service", list(shipping.RATES), "Shipping service")
        f.done()
        if f.bool("save_address"):
            g.user.street, g.user.city, g.user.state, g.user.zip = addr["street"], addr["city"], addr["state"], addr["zip"]
        order = place_order(g.user, addr, service)
        flash(f"Order #{order.id} placed! Your sellers have been notified.", "success")
        return redirect(url_for("shop.order", oid=order.id))
    subtotal = sum(c.product.price_cents * c.qty for c in lines)
    return render_template("checkout.html", lines=lines, subtotal=subtotal, origin=shipping.ORIGIN)


# ---------- orders ----------

def order_for_viewer(oid):
    """(order, items visible to the viewer). Sellers only see their own lines; others get 404."""
    order = db.get_or_404(Order, oid)
    u = g.user
    if u.role == "admin" or (u.role == "customer" and order.user_id == u.id):
        return order, order.items
    if u.role == "seller" and u.store:
        mine = [i for i in order.items if i.store_id == u.store.id]
        if mine:
            return order, mine
    abort(404)


@bp.get("/orders")
@require("customer")
def orders():
    rows = Order.query.filter_by(user_id=g.user.id).order_by(Order.id.desc()).all()
    return render_template("orders.html", orders=rows)


@bp.get("/orders/<int:oid>")
@require()
def order(oid):
    o, items = order_for_viewer(oid)
    return render_template("order.html", o=o, items=items, window=setting("return_window_days"))


@bp.post("/orders/<int:oid>/cancel")
@require("customer")
def cancel_order(oid):
    o, _ = order_for_viewer(oid)
    if not o.cancellable:
        abort(409, "This order can't be cancelled because part of it has already shipped. Request a return instead.")
    for i in o.items:
        if i.status == "pending":
            set_item_status(i, "cancelled", "customer")
    db.session.commit()
    flash(f"Order #{o.id} cancelled. Your refund of {o.total_cents / 100:,.2f} USD is on its way.", "success")
    return redirect(url_for("shop.order", oid=o.id))


def change_item(item_id, new_status, form):
    """One entry point for every item transition (customer return, seller fulfilment, admin override)."""
    item = db.get_or_404(OrderItem, item_id)
    u = g.user
    if u.role == "customer" and item.order.user_id != u.id:
        abort(404)
    if u.role == "seller" and (not u.store or item.store_id != u.store.id):
        abort(404)
    f = Form(form)
    if new_status == "return_requested":
        reason = f.str("reason", "Return reason", min_len=5, max_len=500)
        f.done()
        if u.role != "admin" and item.updated_at < now() - timedelta(days=setting("return_window_days")):
            abort(409, "The return window for this item has closed.")
        item.return_reason = reason
    if new_status == "shipped":
        tracking = f.str("tracking", "Tracking number", required=False, max_len=40).upper()
        if tracking and not (tracking.startswith("1Z") and len(tracking) == 18 and tracking.isalnum()):
            f.errors["tracking"] = "UPS tracking numbers look like 1Z followed by 16 letters/digits."
        f.done()
        item.tracking = tracking or "1Z" + secrets.token_hex(8).upper()
    set_item_status(item, new_status, u.role, override=u.role == "admin")
    if u.role == "admin":
        audit("order_item.override", f"item {item.id} (order {item.order_id}) -> {new_status}")
    db.session.commit()
    return item


@bp.post("/order-items/<int:iid>/<any(return_requested, shipped, delivered, cancelled, returned, return_rejected):status>")
@require("customer", "seller")
def item_action(iid, status):
    item = change_item(iid, status, request.form)
    flash(f"{item.name}: {status.replace('_', ' ')}.", "success")
    return redirect(safe_next(request.form.get("next"), url_for("shop.order", oid=item.order_id)))


# ---------- messaging ----------

def conversation_for_viewer(cid):
    c = db.get_or_404(Conversation, cid)
    u = g.user
    if u.role == "admin" or c.customer_id == u.id or (u.store and c.store_id == u.store.id):
        return c
    abort(404)


@bp.get("/messages")
@require()
def inbox():
    u = g.user
    q = Conversation.query
    if u.role == "customer":
        q = q.filter_by(customer_id=u.id)
    elif u.role == "seller":
        q = q.filter_by(store_id=u.store.id if u.store else -1)
    return render_template("messages.html", convs=q.order_by(Conversation.updated_at.desc()).limit(200).all())


@bp.route("/messages/new", methods=["GET", "POST"])
@require("customer")
def new_message():
    src = request.form if request.method == "POST" else request.args
    f = Form(src)
    store_id = f.int("store_id", "Store", lo=1)
    product_id = f.int("product_id", "Product", lo=1, required=False)
    order_id = f.int("order_id", "Order", lo=1, required=False)
    f.done()
    s = db.session.get(Store, store_id)
    if not s or not s.is_active:
        abort(404, "That store isn't accepting messages.")
    p = db.session.get(Product, product_id) if product_id else None
    o = db.session.get(Order, order_id) if order_id else None
    if product_id and (not p or p.store_id != s.id):
        raise Invalid({"product_id": "That product isn't sold by this store."})
    if order_id and (not o or o.user_id != g.user.id or all(i.store_id != s.id for i in o.items)):
        raise Invalid({"order_id": "That order doesn't include items from this store."})
    if request.method == "POST":
        subject = f.str("subject", "Subject", max_len=140, min_len=3)
        body = f.str("body", "Message", max_len=4000, min_len=2)
        f.done()
        c = Conversation(customer_id=g.user.id, store_id=s.id, product_id=product_id, order_id=order_id,
                         subject=subject)
        c.messages.append(Message(sender_id=g.user.id, body=body))
        db.session.add(c)
        db.session.commit()
        flash(f"Message sent to {s.name}. They'll reply here.", "success")
        return redirect(url_for("shop.conversation", cid=c.id))
    default = f"Question about {p.name}" if p else (f"Order #{o.id}" if o else f"Question for {s.name}")
    return render_template("conversation.html", c=None, s=s, p=p, o=o, default_subject=default)


@bp.route("/messages/<int:cid>", methods=["GET", "POST"])
@require()
def conversation(cid):
    c = conversation_for_viewer(cid)
    if request.method == "POST":
        f = Form(request.form)
        body = f.str("body", "Message", max_len=4000, min_len=1)
        f.done()
        c.messages.append(Message(sender_id=g.user.id, body=body))
        c.updated_at = now()
        if g.user.role == "admin":
            audit("message.admin_reply", f"conversation {c.id}")
        db.session.commit()
        return redirect(url_for("shop.conversation", cid=c.id) + "#latest")
    return render_template("conversation.html", c=c, s=c.store, p=c.product, o=None)


def unread_hint():
    """Conversations whose last message is from the other party, for the nav badge."""
    u = g.get("user")
    if not u:
        return 0
    last = db.session.query(Message.conversation_id, func.max(Message.id).label("m")).group_by(
        Message.conversation_id).subquery()
    q = db.session.query(func.count()).select_from(Conversation).join(last, last.c.conversation_id == Conversation.id
                                                                     ).join(Message, Message.id == last.c.m)
    if u.role == "customer":
        q = q.filter(Conversation.customer_id == u.id)
    elif u.role == "seller" and u.store:
        q = q.filter(Conversation.store_id == u.store.id)
    else:
        return 0
    return q.filter(Message.sender_id != u.id).scalar()


@bp.app_context_processor
def nav_counts():
    u = g.get("user")
    cart_count = (db.session.query(func.coalesce(func.sum(CartItem.qty), 0)).filter_by(user_id=u.id).scalar()
                  if u and u.role == "customer" else 0)
    return {"cart_count": cart_count, "awaiting_reply": unread_hint()}
