"""Forty Acres Market: a multi-vendor marketplace for customers, sellers and admins.

Error contract (every route): invalid input -> 400 (JSON {"error"} under /api, flash +
redirect back for HTML forms), missing auth -> 401 (JSON, or redirect to /login),
wrong role or not the owner -> 403, unknown id -> 404, state conflict -> 409,
non-JSON body on a JSON API -> 415, throttled -> 429.
"""
import functools
import os
import re
import secrets
import sqlite3
import string
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from urllib.parse import urlparse

from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

import chatbot
import shipping
from db import close_db, get_db, init_db
from db import settings as load_settings

app = Flask(__name__)
os.makedirs(app.instance_path, exist_ok=True)


def _secret_key():
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    path = os.path.join(app.instance_path, "secret_key")
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(secrets.token_hex(32))
        os.chmod(path, 0o600)
    with open(path) as f:
        return f.read().strip()


app.config.update(
    SECRET_KEY=_secret_key(),
    DATABASE=os.environ.get("DATABASE", os.path.join(app.instance_path, "market.db")),
    UPLOAD_FOLDER=os.path.join(app.static_folder, "uploads"),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)
app.teardown_appcontext(close_db)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
with app.app_context():
    init_db()

CATEGORIES = ["Apparel", "Accessories", "Home & Living", "Art & Prints", "Electronics",
              "Books", "Outdoors", "Food & Drink", "Other"]
STATUS_LABELS = {
    "placed": "Placed", "shipped": "Shipped", "delivered": "Delivered", "cancelled": "Cancelled",
    "return_requested": "Return requested", "returned": "Returned", "return_rejected": "Return rejected",
}
# (from, to) -> roles allowed to make that move. Admins may set any status (override).
TRANSITIONS = {
    ("placed", "cancelled"): {"customer", "seller"},
    ("placed", "shipped"): {"seller"},
    ("shipped", "delivered"): {"seller"},
    ("delivered", "return_requested"): {"customer"},
    ("return_requested", "returned"): {"seller"},
    ("return_requested", "return_rejected"): {"seller"},
}
RESTOCKED = {"cancelled", "returned"}  # statuses where the units are back on the shelf
NOT_REVENUE = "('cancelled', 'returned')"
US_STATES = set("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH "
                "NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split())
EMAIL_RE = r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}"
ZIP_RE = r"\d{5}(-\d{4})?"
PAGE_SIZE = 24
VISIBLE = "(p.is_active = 1 AND s.is_active = 1 AND u.is_active = 1 AND u.role = 'seller')"
PRODUCT_FROM = "FROM products p JOIN stores s ON s.id = p.store_id JOIN users u ON u.id = s.seller_id"
SORTS = {"new": "p.created_at DESC, p.id DESC", "popular": "sold DESC, p.id DESC",
         "price_asc": "p.price_cents ASC, p.id", "price_desc": "p.price_cents DESC, p.id"}
STOPWORDS = set("the a an and or for with what where when how do does is are you your have has any can i "
                "me my to of in on it this that there looking need want find show some".split())


# ---------------------------------------------------------------- errors & helpers

class BadInput(Exception):
    """User-correctable input problem -> 400."""


def wants_json():
    return request.path.startswith("/api/")


@app.errorhandler(BadInput)
def handle_bad_input(e):
    if wants_json():
        return jsonify(error=str(e), status=400), 400
    if request.method == "POST":
        flash(str(e), "error")
        return redirect(back())
    return render_template("error.html", code=400, message=str(e)), 400


@app.errorhandler(sqlite3.IntegrityError)
def handle_integrity(_e):
    get_db().rollback()
    msg = "That change conflicts with existing data. Please refresh and try again."
    if wants_json():
        return jsonify(error=msg, status=409), 409
    return render_template("error.html", code=409, message=msg), 409


@app.errorhandler(HTTPException)
def handle_http(e):
    if wants_json():
        return jsonify(error=e.description, status=e.code), e.code
    if e.code == 401:
        flash("Please sign in to continue.", "error")
        nxt = request.full_path.rstrip("?") if request.method == "GET" else None
        return redirect(url_for("login", next=nxt))
    return render_template("error.html", code=e.code, message=e.description), e.code


def back():
    ref = request.referrer
    if ref and urlparse(ref).netloc == request.host:
        return ref
    return url_for("index")


def safe_next(target):
    return bool(target) and target.startswith("/") and not target.startswith("//") and "\\" not in target


_hits = defaultdict(deque)


def throttle(key, limit, window, record=True):
    # ponytail: in-process limiter, move to Redis once there is more than one worker.
    now = time.monotonic()
    q = _hits[key]
    while q and q[0] <= now - window:
        q.popleft()
    if len(q) >= limit:
        abort(429, "Too many requests. Please wait a few minutes and try again.")
    if record:
        q.append(now)


def _src():
    if request.is_json:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise BadInput("Request body must be a JSON object.")
        return data
    return request.form


def require_json():
    if not request.is_json:
        abort(415, "Send a JSON body with Content-Type: application/json.")
    return _src()


def text(name, label=None, *, required=True, max_len=200, pattern=None, src=None):
    src = _src() if src is None else src
    raw = src.get(name)
    if isinstance(raw, (dict, list, bool)):
        raw = None
    value = "" if raw is None else str(raw).strip()
    label = label or name.replace("_", " ").capitalize()
    if not value:
        if required:
            raise BadInput(f"{label} is required.")
        return ""
    if len(value) > max_len:
        raise BadInput(f"{label} must be at most {max_len} characters.")
    if pattern and not re.fullmatch(pattern, value):
        raise BadInput(f"{label} is not valid.")
    return value


def num(name, label=None, *, lo, hi, cast=float, required=True, default=None, src=None):
    label = label or name.replace("_", " ").capitalize()
    value = text(name, label, required=required, max_len=24, src=src)
    if not value:
        return default
    try:
        n = cast(value)
    except ValueError:
        raise BadInput(f"{label} must be a {'whole ' if cast is int else ''}number.") from None
    if not lo <= n <= hi:  # also rejects NaN
        raise BadInput(f"{label} must be between {lo:g} and {hi:g}.")
    return n


def cents(name, label, *, lo="0.01", hi="100000"):
    value = text(name, label, max_len=16).replace("$", "").replace(",", "")
    try:
        d = Decimal(value)
    except InvalidOperation:
        raise BadInput(f"{label} must be a dollar amount.") from None
    if not d.is_finite() or d != d.quantize(Decimal("0.01")) or not Decimal(lo) <= d <= Decimal(hi):
        raise BadInput(f"{label} must be between ${lo} and ${hi} with at most 2 decimals.")
    return int(d * 100)


def pct_of(amount_cents, pct):
    return int((Decimal(amount_cents) * Decimal(pct) / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def read_address(src=None):
    addr = {
        "name": text("name", "Recipient name", max_len=100, src=src),
        "street": text("street", "Street address", max_len=200, src=src),
        "city": text("city", "City", max_len=100, src=src),
        "state": text("state", "State", max_len=2, src=src).upper(),
        "zip": text("zip", "ZIP code", max_len=10, pattern=ZIP_RE, src=src),
    }
    if addr["state"] not in US_STATES:
        raise BadInput("State must be a 2-letter US state code.")
    return addr


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC, same as SQLite datetime('now')


def now_str():
    return utcnow().strftime("%Y-%m-%d %H:%M:%S")


def log_event(entity, entity_id, action, note=""):
    get_db().execute("INSERT INTO events (actor_id, entity, entity_id, action, note) VALUES (?, ?, ?, ?, ?)",
                     (g.user["id"] if g.user else None, entity, entity_id, action, note))


# ---------------------------------------------------------------- auth plumbing

@app.before_request
def load_user():
    g.user = None
    uid = session.get("uid")
    if uid:
        user = get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        if user and user["is_active"]:
            g.user = user
        else:
            session.clear()  # deactivated accounts are signed out on their next request


@app.before_request
def csrf_protect():
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        # Cross-site forms can't send application/json without a CORS preflight, so JSON APIs are safe.
        if wants_json() and request.is_json:
            return
        token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or ""
        expected = session.get("csrf")
        if not expected or not secrets.compare_digest(token, expected):
            abort(400, "Your session expired or the form is stale (CSRF check failed). Reload and try again.")


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


@app.after_request
def security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; img-src 'self' data:; frame-ancestors 'none'")
    return resp


def login_required(*roles):
    def deco(view):
        @functools.wraps(view)
        def wrapper(*args, **kwargs):
            if g.user is None:
                abort(401, "Sign in required.")
            if roles and g.user["role"] not in roles:
                abort(403, f"This page is for {' or '.join(roles)} accounts.")
            return view(*args, **kwargs)
        return wrapper
    return deco


def is_admin():
    return g.user is not None and g.user["role"] == "admin"


def start_session(uid):
    session.clear()
    session.permanent = True
    session["uid"] = uid


def my_store():
    store = get_db().execute("SELECT * FROM stores WHERE seller_id = ?", (g.user["id"],)).fetchone()
    if store is None:
        abort(409, "Your account has no store yet. Contact an administrator.")
    return store


def conv_scope():
    if is_admin():
        return "1 = 1", []
    if g.user["role"] == "seller":
        return "c.store_id IN (SELECT id FROM stores WHERE seller_id = ?)", [g.user["id"]]
    return "c.customer_id = ?", [g.user["id"]]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.context_processor
def inject_globals():
    ctx = {"settings": load_settings(), "categories": CATEGORIES, "status_labels": STATUS_LABELS,
           "cart_count": 0, "unread": 0}
    user = g.get("user")
    if user:
        db = get_db()
        if user["role"] == "customer":
            ctx["cart_count"] = db.execute("SELECT COALESCE(SUM(qty), 0) FROM cart_items WHERE user_id = ?",
                                           (user["id"],)).fetchone()[0]
        if user["role"] != "admin":
            clause, params = conv_scope()
            ctx["unread"] = db.execute(
                f"SELECT COUNT(*) FROM messages m JOIN conversations c ON c.id = m.conversation_id "
                f"WHERE {clause} AND m.sender_id != ? AND m.read_at IS NULL", params + [user["id"]]).fetchone()[0]
    return ctx


@app.template_filter("money")
def money_filter(c):
    return f"${(c or 0) / 100:,.2f}"


@app.template_filter("dt")
def dt_filter(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").strftime("%b %-d, %Y")
    except (TypeError, ValueError):
        return s or ""


# ---------------------------------------------------------------- accounts

@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("index"))
    if request.method == "POST":
        name = text("name", max_len=100)
        email = text("email", max_len=254, pattern=EMAIL_RE).lower()
        password = text("password", max_len=128)
        if len(password) < 8:
            raise BadInput("Password must be at least 8 characters.")
        role = text("role")
        if role not in ("customer", "seller"):
            raise BadInput("Choose a customer or seller account.")
        store_name = text("store_name", "Store name", max_len=80) if role == "seller" else None
        db = get_db()
        if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise BadInput("An account with that email already exists. Try signing in.")
        if store_name and db.execute("SELECT 1 FROM stores WHERE name = ?", (store_name,)).fetchone():
            raise BadInput("That store name is taken.")
        uid = db.execute("INSERT INTO users (email, password_hash, name, role) VALUES (?, ?, ?, ?)",
                         (email, generate_password_hash(password), name, role)).lastrowid
        if store_name:
            db.execute("INSERT INTO stores (seller_id, name) VALUES (?, ?)", (uid, store_name))
        db.commit()
        start_session(uid)
        flash(f"Welcome to Forty Acres Market, {name}!", "success")
        return redirect(url_for("seller") if role == "seller" else url_for("index"))
    return render_template("auth.html", mode="register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        key = f"login:{request.remote_addr}"
        throttle(key, 10, 300, record=False)  # only failures count toward the limit
        email = text("email", max_len=254).lower()
        password = text("password", max_len=128)
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            _hits[key].append(time.monotonic())
            raise BadInput("Invalid email or password.")
        if not user["is_active"]:
            raise BadInput("This account has been deactivated. Contact an administrator.")
        start_session(user["id"])
        nxt = request.args.get("next", "")
        if safe_next(nxt):
            return redirect(nxt)
        return redirect({"seller": url_for("seller"), "admin": url_for("admin")}.get(user["role"], url_for("index")))
    return render_template("auth.html", mode="login")


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/account", methods=["GET", "POST"])
@login_required()
def account():
    if request.method == "POST":
        name = text("name", max_len=100)
        street = text("street", "Street address", required=False, max_len=200)
        city = text("city", required=False, max_len=100)
        state = text("state", required=False, max_len=2).upper()
        zip_ = text("zip", "ZIP code", required=False, max_len=10, pattern=ZIP_RE)
        if state and state not in US_STATES:
            raise BadInput("State must be a 2-letter US state code.")
        get_db().execute("UPDATE users SET name = ?, street = ?, city = ?, state = ?, zip = ? WHERE id = ?",
                         (name, street, city, state, zip_, g.user["id"]))
        get_db().commit()
        flash("Profile saved.", "success")
        return redirect(url_for("account"))
    return render_template("account.html")


@app.post("/account/password")
@login_required()
def change_password():
    current = text("current_password", "Current password", max_len=128)
    new = text("new_password", "New password", max_len=128)
    if not check_password_hash(g.user["password_hash"], current):
        raise BadInput("Current password is incorrect.")
    if len(new) < 8:
        raise BadInput("New password must be at least 8 characters.")
    get_db().execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new), g.user["id"]))
    get_db().commit()
    flash("Password updated.", "success")
    return redirect(url_for("account"))


@app.post("/account/close")
@login_required("customer", "seller")
def close_account():
    if not check_password_hash(g.user["password_hash"], text("password", max_len=128)):
        raise BadInput("Password is incorrect.")
    db = get_db()
    db.execute("UPDATE users SET is_active = 0 WHERE id = ?", (g.user["id"],))
    log_event("user", g.user["id"], "closed", "Closed by account owner")
    db.commit()
    session.clear()
    flash("Your account has been closed.", "success")
    return redirect(url_for("index"))


# ---------------------------------------------------------------- browsing

def search_products(q="", category="", store_id=None, min_cents=None, max_cents=None, sort="new",
                    limit=PAGE_SIZE, offset=0, match_any=False):
    where, params, term_clauses = [VISIBLE], [], []
    for term in q.split()[:8]:
        like = "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        term_clauses.append("(p.name LIKE ? ESCAPE '\\' OR p.description LIKE ? ESCAPE '\\' "
                            "OR p.category LIKE ? ESCAPE '\\' OR s.name LIKE ? ESCAPE '\\')")
        params += [like] * 4
    if term_clauses:
        where.append("(" + (" OR " if match_any else " AND ").join(term_clauses) + ")")
    if category:
        where.append("p.category = ?")
        params.append(category)
    if store_id:
        where.append("s.id = ?")
        params.append(store_id)
    if min_cents is not None:
        where.append("p.price_cents >= ?")
        params.append(min_cents)
    if max_cents is not None:
        where.append("p.price_cents <= ?")
        params.append(max_cents)
    cond = " AND ".join(where)
    db = get_db()
    total = db.execute(f"SELECT COUNT(*) {PRODUCT_FROM} WHERE {cond}", params).fetchone()[0]
    rows = db.execute(
        f"SELECT p.*, s.name AS store_name, (SELECT COALESCE(SUM(oi.qty), 0) FROM order_items oi "
        f"JOIN orders o ON o.id = oi.order_id WHERE oi.product_id = p.id AND o.status NOT IN {NOT_REVENUE}) AS sold "
        f"{PRODUCT_FROM} WHERE {cond} ORDER BY {SORTS[sort]} LIMIT ? OFFSET ?",
        params + [limit, offset]).fetchall()
    return rows, total


@app.route("/")
def index():
    args = request.args
    q = text("q", "Search", required=False, max_len=100, src=args)
    category = text("category", required=False, src=args)
    if category and category not in CATEGORIES:
        raise BadInput("Unknown category.")
    sort = text("sort", required=False, src=args) or "new"
    if sort not in SORTS:
        raise BadInput("Unknown sort order.")
    page = num("page", lo=1, hi=1000, cast=int, required=False, default=1, src=args)
    min_p = num("min", "Minimum price", lo=0, hi=1e6, required=False, src=args)
    max_p = num("max", "Maximum price", lo=0, hi=1e6, required=False, src=args)
    store_id = num("store", "Store", lo=1, hi=2**31, cast=int, required=False, src=args)
    store = None
    if store_id:
        store = get_db().execute("SELECT * FROM stores WHERE id = ? AND is_active = 1", (store_id,)).fetchone()
        if not store:
            abort(404, "That store doesn't exist or is closed.")
    products, total = search_products(
        q, category, store_id,
        None if min_p is None else round(min_p * 100), None if max_p is None else round(max_p * 100),
        sort, PAGE_SIZE, (page - 1) * PAGE_SIZE)
    pages = max(1, -(-total // PAGE_SIZE))
    return render_template("index.html", products=products, total=total, page=page, pages=pages,
                           q=q, category=category, sort=sort, min_p=min_p, max_p=max_p, store=store)


def fetch_product(pid):
    return get_db().execute(
        f"SELECT p.*, s.name AS store_name, s.description AS store_description, s.seller_id, "
        f"{VISIBLE} AS visible {PRODUCT_FROM} WHERE p.id = ?", (pid,)).fetchone()


@app.route("/products/<int:pid>")
def product(pid):
    p = fetch_product(pid)
    if not p or (not p["visible"] and not (g.user and (is_admin() or g.user["id"] == p["seller_id"]))):
        abort(404, "This product doesn't exist or is no longer available.")
    related = [r for r in search_products(category=p["category"], limit=5, sort="popular")[0] if r["id"] != pid][:4]
    orders = []
    if g.user and g.user["role"] == "customer":
        orders = get_db().execute("SELECT id, created_at FROM orders WHERE customer_id = ? AND store_id = ? "
                                  "ORDER BY id DESC LIMIT 10", (g.user["id"], p["store_id"])).fetchall()
    return render_template("product.html", p=p, related=related, orders=orders)


# ---------------------------------------------------------------- cart & checkout

def cart_groups(uid):
    """Cart lines grouped per store: {store_id: {"store_name", "items": [...]}}."""
    rows = get_db().execute(
        f"SELECT c.qty, p.id AS product_id, p.name, p.price_cents, p.stock, p.image, p.weight_lb, p.length_in, "
        f"p.width_in, p.height_in, s.id AS store_id, s.name AS store_name, {VISIBLE} AS visible "
        f"FROM cart_items c JOIN products p ON p.id = c.product_id JOIN stores s ON s.id = p.store_id "
        f"JOIN users u ON u.id = s.seller_id WHERE c.user_id = ? ORDER BY s.name, p.name", (uid,)).fetchall()
    groups = {}
    for r in rows:
        groups.setdefault(r["store_id"], {"store_name": r["store_name"], "items": []})["items"].append(dict(r))
    return groups


def quote_groups(groups, zip_code, s):
    """Quote every store's shipment separately, then total per UPS service."""
    free_over = int(Decimal(s["free_ground_over"]) * 100)
    shipments, destination = [], None
    for store_id, grp in groups.items():
        q = shipping.quote(zip_code, grp["items"], fuel_pct=float(s["fuel_surcharge_pct"]),
                           residential_fee=float(s["residential_fee"]))
        destination = q["destination"]
        subtotal = sum(i["price_cents"] * i["qty"] for i in grp["items"])
        for svc in q["services"]:
            svc["free"] = svc["code"] == "03" and free_over > 0 and subtotal >= free_over
            if svc["free"]:
                svc["cents"] = 0
        shipments.append({"store_id": store_id, "store_name": grp["store_name"], "subtotal_cents": subtotal,
                          "packages": q["packages"], "services": q["services"]})
    totals = []
    for code, (name, *_rest) in shipping.SERVICES.items():
        per = [next((x for x in sh["services"] if x["code"] == code), None) for sh in shipments]
        if all(per):
            totals.append({"code": code, "name": name, "cents": sum(x["cents"] for x in per),
                           "transit_days": max(x["transit_days"] for x in per),
                           "delivery_date": max(x["delivery_date"] for x in per)})
    return {"origin": shipping.ORIGIN, "destination": destination, "shipments": shipments, "services": totals}


def parse_items(raw):
    if not isinstance(raw, list) or not 1 <= len(raw) <= 50:
        raise BadInput("items must be a list of 1 to 50 {product_id, qty} objects.")
    groups = {}
    for it in raw:
        if not isinstance(it, dict):
            raise BadInput("Each item must be an object with product_id and qty.")
        pid, qty = it.get("product_id"), it.get("qty", 1)
        if type(pid) is not int or type(qty) is not int or pid < 1 or not 1 <= qty <= 99:
            raise BadInput("product_id must be a positive integer and qty an integer from 1 to 99.")
        p = fetch_product(pid)
        if not p or not p["visible"]:
            raise BadInput(f"Product {pid} is not available.")
        item = dict(p) | {"qty": qty, "product_id": pid}
        groups.setdefault(p["store_id"], {"store_name": p["store_name"], "items": []})["items"].append(item)
    return groups


@app.route("/cart")
@login_required("customer")
def cart():
    groups = cart_groups(g.user["id"])
    subtotal = sum(i["price_cents"] * i["qty"] for grp in groups.values() for i in grp["items"])
    return render_template("cart.html", groups=groups, subtotal=subtotal)


@app.post("/cart/add")
@login_required("customer")
def cart_add():
    pid = num("product_id", "Product", lo=1, hi=2**31, cast=int)
    qty = num("qty", "Quantity", lo=1, hi=99, cast=int, required=False, default=1)
    p = fetch_product(pid)
    if not p or not p["visible"]:
        abort(404, "This product is not available.")
    db = get_db()
    have = db.execute("SELECT qty FROM cart_items WHERE user_id = ? AND product_id = ?",
                      (g.user["id"], pid)).fetchone()
    total = qty + (have["qty"] if have else 0)
    if total > p["stock"]:
        raise BadInput(f"Only {p['stock']} of {p['name']} in stock.")
    db.execute("INSERT INTO cart_items (user_id, product_id, qty) VALUES (?, ?, ?) "
               "ON CONFLICT (user_id, product_id) DO UPDATE SET qty = excluded.qty", (g.user["id"], pid, total))
    db.commit()
    flash(f"Added {p['name']} to your cart.", "success")
    return redirect(url_for("cart"))


@app.post("/cart/update")
@login_required("customer")
def cart_update():
    pid = num("product_id", "Product", lo=1, hi=2**31, cast=int)
    qty = num("qty", "Quantity", lo=0, hi=99, cast=int)
    db = get_db()
    if qty == 0:
        db.execute("DELETE FROM cart_items WHERE user_id = ? AND product_id = ?", (g.user["id"], pid))
    else:
        p = fetch_product(pid)
        if not p:
            abort(404, "This product doesn't exist.")
        if qty > p["stock"]:
            raise BadInput(f"Only {p['stock']} of {p['name']} in stock.")
        if not db.execute("UPDATE cart_items SET qty = ? WHERE user_id = ? AND product_id = ?",
                          (qty, g.user["id"], pid)).rowcount:
            abort(404, "That item isn't in your cart.")
    db.commit()
    return redirect(url_for("cart"))


@app.post("/api/shipping/rates")
def api_shipping_rates():
    """Quote UPS services from Austin. Body: {"zip", "items"?: [{product_id, qty}]}; no items = your cart."""
    data = require_json()
    zip_code = text("zip", "ZIP code", max_len=10, pattern=ZIP_RE, src=data)
    if "items" in data:
        groups = parse_items(data["items"])
    else:
        if g.user is None:
            abort(401, "Sign in to quote your cart, or pass an items list.")
        if g.user["role"] != "customer":
            abort(403, "Only customer accounts have a cart; pass an items list instead.")
        groups = cart_groups(g.user["id"])
        if not groups:
            raise BadInput("Your cart is empty.")
    try:
        return jsonify(quote_groups(groups, zip_code, load_settings()))
    except shipping.ShippingError as e:
        raise BadInput(str(e)) from None


@app.post("/api/checkout")
@login_required("customer")
def api_checkout():
    """Place one order per store from the cart. Body: {service, name, street, city, state, zip, save_address?}."""
    data = require_json()
    service = text("service", "Shipping service", max_len=4, src=data)
    if service not in shipping.SERVICES:
        raise BadInput("Unknown shipping service code.")
    addr = read_address(data)
    s = load_settings()
    db = get_db()
    db.execute("BEGIN IMMEDIATE")  # serialize stock checks against other checkouts
    try:
        groups = cart_groups(g.user["id"])
        if not groups:
            raise BadInput("Your cart is empty.")
        problems = [i["name"] + (" (unavailable)" if not i["visible"] else f" (only {i['stock']} left)")
                    for grp in groups.values() for i in grp["items"] if not i["visible"] or i["qty"] > i["stock"]]
        if problems:
            abort(409, "Please update your cart: " + ", ".join(problems) + ".")
        try:
            quote = quote_groups(groups, addr["zip"], s)
        except shipping.ShippingError as e:
            raise BadInput(str(e)) from None
        ref = "FA-" + secrets.token_hex(4).upper()
        order_ids, grand_total = [], 0
        for sh in quote["shipments"]:
            svc = next((x for x in sh["services"] if x["code"] == service), None)
            if svc is None:
                raise BadInput(f"{shipping.SERVICES[service][0]} isn't available to {addr['state']}.")
            subtotal = sh["subtotal_cents"]
            tax = pct_of(subtotal, s["tax_rate_pct"])
            total = subtotal + svc["cents"] + tax
            oid = db.execute(
                "INSERT INTO orders (checkout_ref, customer_id, store_id, status, subtotal_cents, shipping_cents, "
                "tax_cents, total_cents, ship_service, ship_name, ship_street, ship_city, ship_state, ship_zip) "
                "VALUES (?, ?, ?, 'placed', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ref, g.user["id"], sh["store_id"], subtotal, svc["cents"], tax, total, svc["name"],
                 addr["name"], addr["street"], addr["city"], addr["state"], addr["zip"])).lastrowid
            for item in groups[sh["store_id"]]["items"]:
                if not db.execute("UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
                                  (item["qty"], item["product_id"], item["qty"])).rowcount:
                    abort(409, f"{item['name']} just sold out. Please update your cart.")
                db.execute("INSERT INTO order_items (order_id, product_id, name, price_cents, qty) "
                           "VALUES (?, ?, ?, ?, ?)",
                           (oid, item["product_id"], item["name"], item["price_cents"], item["qty"]))
            log_event("order", oid, "placed", f"{svc['name']} to {addr['zip']}")
            order_ids.append(oid)
            grand_total += total
        db.execute("DELETE FROM cart_items WHERE user_id = ?", (g.user["id"],))
        if data.get("save_address") is True:
            db.execute("UPDATE users SET street = ?, city = ?, state = ?, zip = ? WHERE id = ?",
                       (addr["street"], addr["city"], addr["state"], addr["zip"], g.user["id"]))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return jsonify(checkout_ref=ref, order_ids=order_ids, total_cents=grand_total,
                   redirect=url_for("orders", placed=ref)), 201


# ---------------------------------------------------------------- orders

def load_order(oid):
    o = get_db().execute(
        "SELECT o.*, s.name AS store_name, s.seller_id, u.name AS customer_name, u.email AS customer_email "
        "FROM orders o JOIN stores s ON s.id = o.store_id JOIN users u ON u.id = o.customer_id WHERE o.id = ?",
        (oid,)).fetchone()
    if not o:
        abort(404, "Order not found.")
    if not (is_admin() or g.user["id"] in (o["customer_id"], o["seller_id"])):
        abort(403, "You don't have access to this order.")
    return o


def actor_role(o):
    if is_admin():
        return "admin"
    return "customer" if g.user["id"] == o["customer_id"] else "seller"


def return_deadline(o, days):
    if not o["delivered_at"]:
        return None
    return datetime.strptime(o["delivered_at"], "%Y-%m-%d %H:%M:%S") + timedelta(days=days)


@app.route("/orders")
@login_required("customer")
def orders():
    db = get_db()
    rows = db.execute("SELECT o.*, s.name AS store_name FROM orders o JOIN stores s ON s.id = o.store_id "
                      "WHERE o.customer_id = ? ORDER BY o.id DESC", (g.user["id"],)).fetchall()
    items = {}
    for r in db.execute("SELECT oi.* FROM order_items oi JOIN orders o ON o.id = oi.order_id WHERE o.customer_id = ?",
                        (g.user["id"],)):
        items.setdefault(r["order_id"], []).append(r)
    return render_template("orders.html", orders=rows, items=items, placed=request.args.get("placed", ""))


@app.route("/orders/<int:oid>")
@login_required()
def order_detail(oid):
    o = load_order(oid)
    db = get_db()
    items = db.execute("SELECT oi.*, p.image FROM order_items oi LEFT JOIN products p ON p.id = oi.product_id "
                       "WHERE oi.order_id = ?", (oid,)).fetchall()
    events = db.execute("SELECT e.*, u.name AS actor_name, u.role AS actor_role FROM events e "
                        "LEFT JOIN users u ON u.id = e.actor_id WHERE e.entity = 'order' AND e.entity_id = ? "
                        "ORDER BY e.id", (oid,)).fetchall()
    role = actor_role(o)
    moves = [to for (frm, to), roles in TRANSITIONS.items() if frm == o["status"] and role in roles]
    deadline = return_deadline(o, int(load_settings()["return_window_days"]))
    if "return_requested" in moves and deadline and utcnow() > deadline:
        moves.remove("return_requested")
    return render_template("order.html", o=o, items=items, events=events, role=role, moves=moves,
                           deadline=deadline)


@app.post("/orders/<int:oid>/status")
@login_required()
def order_status(oid):
    o = load_order(oid)
    role = actor_role(o)
    new = text("status")
    if new not in STATUS_LABELS:
        raise BadInput("Unknown order status.")
    if new == o["status"]:
        raise BadInput(f"The order is already {STATUS_LABELS[new].lower()}.")
    if role != "admin":
        allowed = TRANSITIONS.get((o["status"], new))
        if allowed is None:
            abort(409, f"A {STATUS_LABELS[o['status']].lower()} order can't be changed to "
                       f"{STATUS_LABELS[new].lower()}.")
        if role not in allowed:
            abort(403, f"Only the {' or '.join(sorted(allowed))} can do that.")
    note = text("note", required=False, max_len=500)
    updates = {"status": new}
    if new == "shipped":
        tracking = text("tracking", "Tracking number", required=False, max_len=24).upper().replace(" ", "")
        if tracking and not re.fullmatch(r"1Z[0-9A-Z]{16}", tracking):
            raise BadInput("UPS tracking numbers are 1Z followed by 16 letters or digits.")
        updates["tracking"] = tracking or "1Z" + "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))
    elif new == "delivered":
        updates["delivered_at"] = now_str()
    elif new == "return_requested":
        updates["return_reason"] = text("reason", "Return reason", max_len=500)
        note = note or updates["return_reason"]
        deadline = return_deadline(o, int(load_settings()["return_window_days"]))
        if role != "admin" and deadline and utcnow() > deadline:
            abort(409, f"The return window closed on {deadline:%b %-d, %Y}.")

    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    try:
        items = db.execute("SELECT product_id, qty FROM order_items WHERE order_id = ?", (oid,)).fetchall()
        if o["status"] not in RESTOCKED and new in RESTOCKED:
            for it in items:
                db.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (it["qty"], it["product_id"]))
        elif o["status"] in RESTOCKED and new not in RESTOCKED:  # admin reopening an order
            for it in items:
                if not db.execute("UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
                                  (it["qty"], it["product_id"], it["qty"])).rowcount:
                    abort(409, "Not enough stock to reopen this order.")
        sets = ", ".join(f"{k} = ?" for k in updates)
        db.execute(f"UPDATE orders SET {sets} WHERE id = ?", (*updates.values(), oid))
        log_event("order", oid, new, (f"Admin override: {note}" if role == "admin" else note).strip(": "))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    flash(f"Order #{oid} is now {STATUS_LABELS[new].lower()}.", "success")
    return redirect(url_for("order_detail", oid=oid))


# ---------------------------------------------------------------- messaging

@app.route("/messages")
@login_required()
def inbox():
    clause, params = conv_scope()
    convs = get_db().execute(
        f"SELECT c.*, s.name AS store_name, u.name AS customer_name, "
        f"(SELECT body FROM messages WHERE conversation_id = c.id ORDER BY id DESC LIMIT 1) AS last_body, "
        f"(SELECT COUNT(*) FROM messages WHERE conversation_id = c.id AND sender_id != ? AND read_at IS NULL) "
        f"AS unread_count FROM conversations c JOIN stores s ON s.id = c.store_id "
        f"JOIN users u ON u.id = c.customer_id WHERE {clause} ORDER BY c.updated_at DESC LIMIT 200",
        [g.user["id"]] + params).fetchall()
    return render_template("messages.html", convs=convs, conv=None)


@app.route("/messages/<int:cid>", methods=["GET", "POST"])
@login_required()
def thread(cid):
    db = get_db()
    c = db.execute("SELECT c.*, s.name AS store_name, s.seller_id, u.name AS customer_name FROM conversations c "
                   "JOIN stores s ON s.id = c.store_id JOIN users u ON u.id = c.customer_id WHERE c.id = ?",
                   (cid,)).fetchone()
    if not c:
        abort(404, "Conversation not found.")
    if not (is_admin() or g.user["id"] in (c["customer_id"], c["seller_id"])):
        abort(403, "You aren't part of this conversation.")
    if request.method == "POST":
        body = text("body", "Message", max_len=2000)
        db.execute("INSERT INTO messages (conversation_id, sender_id, body) VALUES (?, ?, ?)", (cid, g.user["id"], body))
        db.execute("UPDATE conversations SET updated_at = datetime('now') WHERE id = ?", (cid,))
        db.commit()
        return redirect(url_for("thread", cid=cid) + "#latest")
    if not is_admin():
        db.execute("UPDATE messages SET read_at = datetime('now') WHERE conversation_id = ? AND sender_id != ? "
                   "AND read_at IS NULL", (cid, g.user["id"]))
        db.commit()
    msgs = db.execute("SELECT m.*, u.name AS sender_name, u.role AS sender_role, p.name AS product_name "
                      "FROM messages m JOIN users u ON u.id = m.sender_id LEFT JOIN products p ON p.id = m.product_id "
                      "WHERE m.conversation_id = ? ORDER BY m.id", (cid,)).fetchall()
    clause, params = conv_scope()
    convs = db.execute(
        f"SELECT c.*, s.name AS store_name, u.name AS customer_name, "
        f"(SELECT body FROM messages WHERE conversation_id = c.id ORDER BY id DESC LIMIT 1) AS last_body, "
        f"0 AS unread_count FROM conversations c JOIN stores s ON s.id = c.store_id "
        f"JOIN users u ON u.id = c.customer_id WHERE {clause} ORDER BY c.updated_at DESC LIMIT 200",
        params).fetchall()
    return render_template("messages.html", convs=convs, conv=c, msgs=msgs)


@app.post("/messages/start")
@login_required("customer")
def message_start():
    store_id = num("store_id", "Store", lo=1, hi=2**31, cast=int)
    product_id = num("product_id", "Product", lo=1, hi=2**31, cast=int, required=False)
    order_id = num("order_id", "Order", lo=1, hi=2**31, cast=int, required=False)
    body = text("body", "Message", max_len=2000)
    db = get_db()
    if not db.execute("SELECT 1 FROM stores WHERE id = ? AND is_active = 1", (store_id,)).fetchone():
        abort(404, "That store doesn't exist or is closed.")
    if product_id and not db.execute("SELECT 1 FROM products WHERE id = ? AND store_id = ?",
                                     (product_id, store_id)).fetchone():
        raise BadInput("That product doesn't belong to this store.")
    if order_id and not db.execute("SELECT 1 FROM orders WHERE id = ? AND store_id = ? AND customer_id = ?",
                                   (order_id, store_id, g.user["id"])).fetchone():
        abort(403, "You can only reference your own orders from this store.")
    db.execute("INSERT OR IGNORE INTO conversations (customer_id, store_id) VALUES (?, ?)", (g.user["id"], store_id))
    cid = db.execute("SELECT id FROM conversations WHERE customer_id = ? AND store_id = ?",
                     (g.user["id"], store_id)).fetchone()["id"]
    db.execute("INSERT INTO messages (conversation_id, sender_id, body, product_id, order_id) VALUES (?, ?, ?, ?, ?)",
               (cid, g.user["id"], body, product_id, order_id))
    db.execute("UPDATE conversations SET updated_at = datetime('now') WHERE id = ?", (cid,))
    db.commit()
    flash("Message sent. The seller will reply here.", "success")
    return redirect(url_for("thread", cid=cid) + "#latest")


# ---------------------------------------------------------------- chatbot

@app.post("/api/chat")
def api_chat():
    """Body: {"messages": [{"role": "user"|"assistant", "content": str}, ...]} ending with a user turn."""
    data = require_json()
    if g.user and g.user["role"] != "customer":
        abort(403, "The shopping assistant is for customers.")
    msgs = data.get("messages")
    if not isinstance(msgs, list) or not 1 <= len(msgs) <= 20:
        raise BadInput("messages must be a list of 1 to 20 turns.")
    history = []
    for i, m in enumerate(msgs):
        expected = "user" if i % 2 == 0 else "assistant"
        if not isinstance(m, dict) or m.get("role") != expected or not isinstance(m.get("content"), str) \
                or not 1 <= len(m["content"].strip()) <= 2000:
            raise BadInput("Turns must alternate user/assistant, start with user, and be 1-2000 characters.")
        history.append({"role": expected, "content": m["content"].strip()})
    if history[-1]["role"] != "user":
        raise BadInput("The last turn must be from the user.")
    throttle(f"chat:{request.remote_addr}", 20, 600)

    last = history[-1]["content"]
    terms = " ".join(w for w in re.findall(r"[a-zA-Z0-9]{3,}", last.lower()) if w not in STOPWORDS)
    products = search_products(terms, sort="popular", limit=5, match_any=True)[0] if terms else []
    lines = ["Products matching the latest question:"] + ([
        f"- #{p['id']} {p['name']} | {money_filter(p['price_cents'])} | {p['category']} | store: {p['store_name']} "
        f"| {'in stock' if p['stock'] else 'sold out'} | page: /products/{p['id']} | {p['description'][:200]}"
        for p in products] or ["(none)"])
    if g.user:
        recent = get_db().execute("SELECT o.id, o.status, o.created_at, o.tracking, s.name AS store_name FROM orders o "
                                  "JOIN stores s ON s.id = o.store_id WHERE o.customer_id = ? ORDER BY o.id DESC "
                                  "LIMIT 5", (g.user["id"],)).fetchall()
        lines.append(f"Signed-in customer: {g.user['name']}. Recent orders:")
        lines += [f"- Order #{o['id']} from {o['store_name']}: {STATUS_LABELS[o['status']]}, placed {o['created_at']}"
                  f"{', UPS ' + o['tracking'] if o['tracking'] else ''} | page: /orders/{o['id']}" for o in recent]
    else:
        lines.append("The visitor is not signed in.")
    s = load_settings()
    policy = {"return_days": s["return_window_days"], "tax": s["tax_rate_pct"]}
    reply = chatbot.ai_reply(history, "\n".join(lines), policy)
    ai = reply is not None
    if not ai:
        reply = chatbot.rule_reply(last, products, policy)
    suggestions = [{"label": p["name"], "url": url_for("product", pid=p["id"])} for p in products[:3]]
    if products:
        suggestions.append({"label": f"Message {products[0]['store_name']}",
                            "url": url_for("product", pid=products[0]["id"]) + "#message"})
    if g.user:
        suggestions.append({"label": "My orders", "url": url_for("orders")})
    return jsonify(reply=reply, suggestions=suggestions, ai=ai)


# ---------------------------------------------------------------- seller

def revenue_series(column, store_id=None, days=30):
    assert column in ("total_cents", "subtotal_cents")
    params = [f"-{days - 1} days"]
    extra = ""
    if store_id:
        extra, params = " AND store_id = ?", params + [store_id]
    rows = get_db().execute(
        f"SELECT date(created_at) AS d, SUM({column}) AS c, COUNT(*) AS n FROM orders "
        f"WHERE status NOT IN {NOT_REVENUE} AND date(created_at) >= date('now', ?){extra} GROUP BY d", params)
    by_day = {r["d"]: r for r in rows}
    today = datetime.now(timezone.utc).date()
    out = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        r = by_day.get(d.isoformat())
        out.append({"date": d.isoformat(), "label": f"{d:%b} {d.day}", "cents": r["c"] if r else 0,
                    "orders": r["n"] if r else 0})
    return out


def managed_product(pid):
    p = fetch_product(pid)
    if not p:
        abort(404, "Product not found.")
    if not (is_admin() or p["seller_id"] == g.user["id"]):
        abort(403, "Sellers can only manage their own products.")
    return p


@app.route("/seller")
@login_required("seller")
def seller():
    store = my_store()
    db = get_db()
    status = request.args.get("status", "")
    if status and status not in STATUS_LABELS:
        raise BadInput("Unknown order status filter.")
    products = db.execute("SELECT * FROM products WHERE store_id = ? ORDER BY is_active DESC, name",
                          (store["id"],)).fetchall()
    order_sql = ("SELECT o.*, u.name AS customer_name, (SELECT SUM(qty) FROM order_items WHERE order_id = o.id) AS units "
                 "FROM orders o JOIN users u ON u.id = o.customer_id WHERE o.store_id = ?")
    params = [store["id"]]
    if status:
        order_sql += " AND o.status = ?"
        params.append(status)
    orders_ = db.execute(order_sql + " ORDER BY (o.status IN ('placed', 'return_requested')) DESC, o.id DESC LIMIT 100",
                         params).fetchall()
    series = revenue_series("subtotal_cents", store["id"])
    fee = load_settings()["platform_fee_pct"]
    gross = sum(d["cents"] for d in series)
    stats = {
        "revenue": gross,
        "payout": gross - pct_of(gross, fee),
        "orders": sum(d["orders"] for d in series),
        "to_ship": db.execute("SELECT COUNT(*) FROM orders WHERE store_id = ? AND status = 'placed'",
                              (store["id"],)).fetchone()[0],
        "returns": db.execute("SELECT COUNT(*) FROM orders WHERE store_id = ? AND status = 'return_requested'",
                              (store["id"],)).fetchone()[0],
        "low_stock": sum(1 for p in products if p["is_active"] and p["stock"] <= 3),
    }
    return render_template("seller.html", store=store, products=products, orders=orders_, series=series,
                           stats=stats, status=status, fee=fee)


@app.post("/seller/store")
@login_required("seller")
def seller_store():
    store = my_store()
    name = text("name", "Store name", max_len=80)
    description = text("description", required=False, max_len=1000)
    if get_db().execute("SELECT 1 FROM stores WHERE name = ? AND id != ?", (name, store["id"])).fetchone():
        raise BadInput("That store name is taken.")
    get_db().execute("UPDATE stores SET name = ?, description = ? WHERE id = ?", (name, description, store["id"]))
    get_db().commit()
    flash("Store updated.", "success")
    return redirect(url_for("seller"))


IMAGE_SIGNATURES = {b"\x89PNG\r\n\x1a\n": "png", b"\xff\xd8\xff": "jpg", b"GIF87a": "gif", b"GIF89a": "gif"}


def save_upload(f):
    """Store an uploaded image under a random name after checking its magic bytes. None if no file."""
    if not f or not f.filename:
        return None
    head = f.stream.read(12)
    f.stream.seek(0)
    ext = next((e for sig, e in IMAGE_SIGNATURES.items() if head.startswith(sig)), None)
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        ext = "webp"
    if not ext:
        raise BadInput("Images must be PNG, JPEG, GIF or WebP (max 5 MB).")
    name = f"{uuid.uuid4().hex}.{ext}"
    f.save(os.path.join(app.config["UPLOAD_FOLDER"], name))
    return name


def delete_upload(name):
    if name:
        try:
            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], name))
        except FileNotFoundError:
            pass


def read_product_form():
    fields = {
        "name": text("name", "Product name", max_len=120),
        "description": text("description", required=False, max_len=4000),
        "category": text("category"),
        "price_cents": cents("price", "Price"),
        "stock": num("stock", "Stock", lo=0, hi=100000, cast=int),
        "weight_lb": num("weight_lb", "Weight", lo=0.01, hi=150),
        "length_in": num("length_in", "Length", lo=0.1, hi=108),
        "width_in": num("width_in", "Width", lo=0.1, hi=108),
        "height_in": num("height_in", "Height", lo=0.1, hi=108),
    }
    if fields["category"] not in CATEGORIES:
        raise BadInput("Choose a category from the list.")
    try:
        shipping.check_item(fields["weight_lb"], fields["length_in"], fields["width_in"], fields["height_in"])
    except shipping.ShippingError as e:
        raise BadInput(f"This item can't ship by UPS: {e}") from None
    return fields


@app.route("/seller/products/new", methods=["GET", "POST"])
@app.route("/seller/products/<int:pid>/edit", methods=["GET", "POST"])
@login_required("seller", "admin")
def product_form(pid=None):
    p = managed_product(pid) if pid else None
    if p is None and is_admin():
        abort(403, "Products are created by sellers. Admins can edit existing products.")
    if request.method == "POST":
        fields = read_product_form()
        image = save_upload(request.files.get("image"))
        db = get_db()
        if p:
            if image:
                fields["image"] = image
            sets = ", ".join(f"{k} = ?" for k in fields)
            db.execute(f"UPDATE products SET {sets} WHERE id = ?", (*fields.values(), pid))
            if is_admin() and p["seller_id"] != g.user["id"]:
                log_event("product", pid, "admin_edit", fields["name"])
            db.commit()
            if image:
                delete_upload(p["image"])
        else:
            fields |= {"image": image, "store_id": my_store()["id"]}
            cols = ", ".join(fields)
            pid = db.execute(f"INSERT INTO products ({cols}) VALUES ({', '.join('?' * len(fields))})",
                             tuple(fields.values())).lastrowid
            db.commit()
        flash("Product saved.", "success")
        return redirect(url_for("product", pid=pid))
    return render_template("product_form.html", p=p)


@app.post("/seller/products/<int:pid>/stock")
@login_required("seller", "admin")
def product_stock(pid):
    managed_product(pid)
    stock = num("stock", "Stock", lo=0, hi=100000, cast=int)
    get_db().execute("UPDATE products SET stock = ? WHERE id = ?", (stock, pid))
    get_db().commit()
    flash("Inventory updated.", "success")
    return redirect(back())


@app.post("/seller/products/<int:pid>/toggle")
@login_required("seller", "admin")
def product_toggle(pid):
    p = managed_product(pid)
    db = get_db()
    db.execute("UPDATE products SET is_active = ? WHERE id = ?", (0 if p["is_active"] else 1, pid))
    if is_admin():
        log_event("product", pid, "deactivated" if p["is_active"] else "activated", p["name"])
    db.commit()
    flash(f"{p['name']} is now {'hidden' if p['is_active'] else 'live'}.", "success")
    return redirect(back())


# ---------------------------------------------------------------- admin

ADMIN_TABS = ("analytics", "users", "stores", "products", "orders", "settings", "activity")


@app.route("/admin")
@login_required("admin")
def admin():
    tab = request.args.get("tab", "analytics")
    if tab not in ADMIN_TABS:
        abort(404, "Unknown admin section.")
    q = text("q", "Search", required=False, max_len=100, src=request.args)
    like = f"%{q}%"
    db = get_db()
    ctx = {"tab": tab, "q": q}
    # ponytail: admin lists cap at 200 rows with a search box; add paging when the platform outgrows that.
    if tab == "analytics":
        series = revenue_series("total_cents")
        s = load_settings()
        gmv = sum(d["cents"] for d in series)
        n = sum(d["orders"] for d in series)
        all_orders = db.execute("SELECT COUNT(*) FROM orders WHERE date(created_at) >= date('now', '-29 days')"
                                ).fetchone()[0]
        returned = db.execute("SELECT COUNT(*) FROM orders WHERE status IN ('returned', 'return_requested') "
                              "AND date(created_at) >= date('now', '-29 days')").fetchone()[0]
        subtotal = db.execute(f"SELECT COALESCE(SUM(subtotal_cents), 0) FROM orders WHERE status NOT IN {NOT_REVENUE} "
                              f"AND date(created_at) >= date('now', '-29 days')").fetchone()[0]
        ctx.update(
            series=series,
            kpis={
                "gmv": gmv, "orders": n, "aov": gmv // n if n else 0,
                "fees": pct_of(subtotal, s["platform_fee_pct"]),
                "return_rate": round(100 * returned / all_orders, 1) if all_orders else 0,
                "customers": db.execute("SELECT COUNT(*) FROM users WHERE role = 'customer' AND is_active = 1").fetchone()[0],
                "sellers": db.execute("SELECT COUNT(*) FROM users WHERE role = 'seller' AND is_active = 1").fetchone()[0],
                "live_products": db.execute(f"SELECT COUNT(*) {PRODUCT_FROM} WHERE {VISIBLE}").fetchone()[0],
            },
            by_status=db.execute("SELECT status, COUNT(*) AS n FROM orders GROUP BY status ORDER BY n DESC").fetchall(),
            top_stores=db.execute(
                f"SELECT s.id, s.name, COUNT(o.id) AS orders, SUM(o.subtotal_cents) AS revenue FROM orders o "
                f"JOIN stores s ON s.id = o.store_id WHERE o.status NOT IN {NOT_REVENUE} "
                f"AND date(o.created_at) >= date('now', '-29 days') GROUP BY s.id ORDER BY revenue DESC LIMIT 5").fetchall(),
            top_products=db.execute(
                f"SELECT p.id, p.name, s.name AS store_name, SUM(oi.qty) AS units, SUM(oi.qty * oi.price_cents) AS revenue "
                f"FROM order_items oi JOIN orders o ON o.id = oi.order_id JOIN products p ON p.id = oi.product_id "
                f"JOIN stores s ON s.id = p.store_id WHERE o.status NOT IN {NOT_REVENUE} "
                f"AND date(o.created_at) >= date('now', '-29 days') GROUP BY p.id ORDER BY units DESC LIMIT 5").fetchall(),
            by_category=db.execute(
                f"SELECT p.category, SUM(oi.qty * oi.price_cents) AS revenue FROM order_items oi "
                f"JOIN orders o ON o.id = oi.order_id JOIN products p ON p.id = oi.product_id "
                f"WHERE o.status NOT IN {NOT_REVENUE} AND date(o.created_at) >= date('now', '-29 days') "
                f"GROUP BY p.category ORDER BY revenue DESC").fetchall(),
        )
    elif tab == "users":
        ctx["rows"] = db.execute("SELECT u.*, s.name AS store_name FROM users u LEFT JOIN stores s ON s.seller_id = u.id "
                                 "WHERE u.email LIKE ? OR u.name LIKE ? ORDER BY u.id DESC LIMIT 200",
                                 (like, like)).fetchall()
    elif tab == "stores":
        ctx["rows"] = db.execute("SELECT s.*, u.name AS seller_name, u.email AS seller_email, u.is_active AS seller_active, "
                                 "(SELECT COUNT(*) FROM products WHERE store_id = s.id) AS products FROM stores s "
                                 "JOIN users u ON u.id = s.seller_id WHERE s.name LIKE ? ORDER BY s.id DESC LIMIT 200",
                                 (like,)).fetchall()
    elif tab == "products":
        ctx["rows"] = db.execute(f"SELECT p.*, s.name AS store_name, {VISIBLE} AS visible {PRODUCT_FROM} "
                                 f"WHERE p.name LIKE ? OR s.name LIKE ? ORDER BY p.id DESC LIMIT 200",
                                 (like, like)).fetchall()
    elif tab == "orders":
        status = request.args.get("status", "")
        if status and status not in STATUS_LABELS:
            raise BadInput("Unknown order status filter.")
        ctx["status"] = status
        ctx["rows"] = db.execute(
            "SELECT o.*, s.name AS store_name, u.name AS customer_name FROM orders o JOIN stores s ON s.id = o.store_id "
            "JOIN users u ON u.id = o.customer_id WHERE (? = '' OR o.status = ?) AND "
            "(u.name LIKE ? OR s.name LIKE ? OR o.checkout_ref LIKE ? OR CAST(o.id AS TEXT) = ?) "
            "ORDER BY o.id DESC LIMIT 200", (status, status, like, like, like, q)).fetchall()
    elif tab == "activity":
        ctx["rows"] = db.execute("SELECT e.*, u.name AS actor_name FROM events e LEFT JOIN users u ON u.id = e.actor_id "
                                 "ORDER BY e.id DESC LIMIT 200").fetchall()
    return render_template("admin.html", **ctx)


@app.post("/admin/users/<int:uid>")
@login_required("admin")
def admin_user(uid):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    if not user:
        abort(404, "User not found.")
    if uid == g.user["id"]:
        raise BadInput("You can't change your own account here. Ask another admin.")
    action = text("action")
    if action in ("activate", "deactivate"):
        db.execute("UPDATE users SET is_active = ? WHERE id = ?", (int(action == "activate"), uid))
        log_event("user", uid, action + "d", user["email"])
    elif action == "set_role":
        role = text("role")
        if role not in ("customer", "seller", "admin"):
            raise BadInput("Unknown role.")
        db.execute("UPDATE users SET role = ? WHERE id = ?", (role, uid))
        if role == "seller" and not db.execute("SELECT 1 FROM stores WHERE seller_id = ?", (uid,)).fetchone():
            db.execute("INSERT INTO stores (seller_id, name) VALUES (?, ?)", (uid, f"{user['name']}'s Shop #{uid}"))
        log_event("user", uid, "role_changed", f"{user['email']}: {user['role']} -> {role}")
    else:
        raise BadInput("Unknown action.")
    db.commit()
    flash("User updated.", "success")
    return redirect(back())


@app.post("/admin/stores/<int:sid>")
@login_required("admin")
def admin_store(sid):
    db = get_db()
    store = db.execute("SELECT * FROM stores WHERE id = ?", (sid,)).fetchone()
    if not store:
        abort(404, "Store not found.")
    action = text("action")
    if action not in ("activate", "deactivate"):
        raise BadInput("Unknown action.")
    db.execute("UPDATE stores SET is_active = ? WHERE id = ?", (int(action == "activate"), sid))
    log_event("store", sid, action + "d", store["name"])
    db.commit()
    flash(f"{store['name']} {action}d.", "success")
    return redirect(back())


@app.post("/admin/settings")
@login_required("admin")
def admin_settings():
    values = {
        "tax_rate_pct": num("tax_rate_pct", "Tax rate", lo=0, hi=25),
        "fuel_surcharge_pct": num("fuel_surcharge_pct", "Fuel surcharge", lo=0, hi=50),
        "residential_fee": num("residential_fee", "Residential surcharge", lo=0, hi=50),
        "free_ground_over": num("free_ground_over", "Free ground threshold", lo=0, hi=10000),
        "return_window_days": num("return_window_days", "Return window", lo=0, hi=365, cast=int),
        "platform_fee_pct": num("platform_fee_pct", "Platform fee", lo=0, hi=50),
        "banner": text("banner", "Announcement banner", required=False, max_len=200),
    }
    db = get_db()
    db.executemany("UPDATE settings SET value = ? WHERE key = ?", [(str(v), k) for k, v in values.items()])
    log_event("settings", 0, "updated", ", ".join(f"{k}={v}" for k, v in values.items() if k != "banner"))
    db.commit()
    flash("Platform settings saved.", "success")
    return redirect(url_for("admin", tab="settings"))


@app.route("/healthz")
def healthz():
    get_db().execute("SELECT 1")
    return jsonify(ok=True)


# ---------------------------------------------------------------- CLI

@app.cli.command("create-admin")
def create_admin_cmd():
    """Create an admin account (prompts for email, name, password)."""
    import click
    email = click.prompt("Email").strip().lower()
    name = click.prompt("Name").strip()
    password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
    if len(password) < 8 or not re.fullmatch(EMAIL_RE, email):
        raise click.ClickException("Need a valid email and a password of 8+ characters.")
    db = get_db()
    db.execute("INSERT INTO users (email, password_hash, name, role) VALUES (?, ?, ?, 'admin')",
               (email, generate_password_hash(password), name))
    db.commit()
    click.echo(f"Admin {email} created.")


@app.cli.command("seed")
def seed_cmd():
    """Load demo accounts, stores, products and 30 days of orders."""
    from seed import seed
    seed(get_db())
