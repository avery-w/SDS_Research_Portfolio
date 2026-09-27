"""Cross-cutting rules every endpoint goes through: auth, roles, CSRF, validation, errors.

Error contract (HTML pages vs /api/* JSON):
  missing auth      HTML: 302 to /login?next=...          API: 401 {"error": "unauthorized"}
  wrong role        HTML: 403 page                         API: 403 {"error": "forbidden"}
  not yours         404 (never reveals that another user's record exists)
  invalid input     HTML: 303 back, errors flashed, input kept   API: 400 {"error": "validation_failed", "fields": {...}}
  bad state/stock   409 {"error": "conflict", "message": ...}
  bad CSRF token    400 page (HTML forms). API writes must be JSON (415 otherwise), which browsers
                    cannot send cross-site without CORS, so the API needs no token.
  too many requests 429
"""
import hmac
import secrets
import time
import uuid
from collections import defaultdict, deque
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

from flask import abort, current_app, flash, g, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import update
from werkzeug.exceptions import HTTPException

from models import RESTOCKED, AuditLog, CartItem, Product, User, db, setting
import shipping


def is_api():
    return request.path.startswith("/api/")


# ---------- auth ----------

def load_user():
    g.user = None
    uid = session.get("uid")
    if uid:
        user = db.session.get(User, uid)
        if user and user.is_active:
            g.user = user
        else:
            session.clear()  # deactivated accounts are signed out on their next request


def login_user(user):
    session.clear()
    session["uid"] = user.id
    session.permanent = True


def require(*roles):
    """Signed-in user required; if roles are given the user must hold one of them."""
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if g.user is None:
                if is_api():
                    abort(401, "Sign in to use this endpoint.")
                flash("Please sign in to continue.", "info")
                return redirect(url_for("shop.login", next=request.full_path))
            if roles and g.user.role not in roles:
                abort(403, f"This area is for {' / '.join(roles)} accounts.")
            return fn(*a, **kw)
        return wrapper
    return deco


def safe_next(url, fallback="/"):
    """Only allow same-site relative redirects (blocks open redirects like //evil.com)."""
    if url and url.startswith("/") and not url.startswith("//") and not urlparse(url).netloc:
        return url
    return fallback


# ---------- CSRF ----------

def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def check_csrf():
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    if is_api():
        if request.method in ("POST", "PUT", "PATCH") and not request.is_json:
            abort(415, "Send a JSON body with Content-Type: application/json.")
        return
    token = request.form.get("csrf_token", "")
    if not hmac.compare_digest(token, session.get("csrf", "")):
        abort(400, "Your form expired or its security token was invalid. Reload the page and try again.")


# ---------- rate limiting ----------

_hits = defaultdict(deque)


def rate_limit(bucket, limit, per_seconds):
    """ponytail: in-process sliding window; use Redis if you run more than one worker."""
    key = (bucket, request.remote_addr)
    q, t = _hits[key], time.monotonic()
    while q and q[0] < t - per_seconds:
        q.popleft()
    if len(q) >= limit:
        abort(429, "Too many requests. Please wait a moment and try again.")
    q.append(t)


# ---------- validation ----------

class Invalid(Exception):
    def __init__(self, errors):
        self.errors = errors


class Form:
    """Collects every field error at once, then `done()` raises Invalid if any failed."""

    def __init__(self, data):
        self.data = data if data is not None else {}
        self.errors = {}

    def _raw(self, name):
        v = self.data.get(name)
        return v.strip() if isinstance(v, str) else v

    def _err(self, name, msg):
        self.errors.setdefault(name, msg)

    def str(self, name, label=None, required=True, max_len=200, min_len=1, default=""):
        v = self._raw(name)
        label = label or name.replace("_", " ").capitalize()
        if v in (None, ""):
            if required:
                self._err(name, f"{label} is required.")
            return default
        if not isinstance(v, str):
            self._err(name, f"{label} must be text.")
            return default
        if len(v) < min_len or len(v) > max_len:
            self._err(name, f"{label} must be {min_len}-{max_len} characters.")
        return v

    def email(self, name="email"):
        v = self.str(name, "Email", max_len=254).lower()
        local, _, domain = v.partition("@")
        if v and (not local or "." not in domain or " " in v):
            self._err(name, "Enter a valid email address.")
        return v

    def int(self, name, label=None, lo=None, hi=None, required=True, default=None):
        v, label = self._raw(name), label or name.replace("_", " ").capitalize()
        if v in (None, ""):
            if required:
                self._err(name, f"{label} is required.")
            return default
        try:
            if isinstance(v, bool) or (isinstance(v, float) and not v.is_integer()):
                raise ValueError
            v = int(v)
        except (TypeError, ValueError):
            self._err(name, f"{label} must be a whole number.")
            return default
        if (lo is not None and v < lo) or (hi is not None and v > hi):
            self._err(name, f"{label} must be between {lo} and {hi}.")
        return v

    def number(self, name, label=None, lo=None, hi=None, required=True, default=None):
        v, label = self._raw(name), label or name.replace("_", " ").capitalize()
        if v in (None, ""):
            if required:
                self._err(name, f"{label} is required.")
            return default
        try:
            d = Decimal(str(v))
            if not d.is_finite() or isinstance(v, bool):
                raise InvalidOperation
        except InvalidOperation:
            self._err(name, f"{label} must be a number.")
            return default
        if (lo is not None and d < Decimal(str(lo))) or (hi is not None and d > Decimal(str(hi))):
            self._err(name, f"{label} must be between {lo} and {hi}.")
        return d

    def money(self, name, label=None, lo=0.01, hi=100000, required=True):
        d = self.number(name, label, lo, hi, required)
        return int((d * 100).quantize(Decimal("1"))) if d is not None else None

    def choice(self, name, options, label=None, required=True, default=None):
        v = self._raw(name)
        if v in (None, "") and not required:
            return default
        if v not in options:
            self._err(name, f"{label or name.capitalize()} must be one of: {', '.join(map(str, options))}.")
            return default
        return v

    def bool(self, name):
        return self._raw(name) in (True, "1", "on", "true", "yes")

    def zip(self, name="zip"):
        v = self.str(name, "ZIP code", max_len=10)
        if v and not (len(v[:5]) == 5 and v[:5].isdigit() and (len(v) == 5 or (len(v) == 10 and v[5] == "-"))):
            self._err(name, "ZIP code must look like 78705 or 78705-1234.")
        return v

    def state(self, name="state"):
        v = self.str(name, "State", max_len=2, min_len=2).upper()
        if v and not v.isalpha():
            self._err(name, "State must be a 2-letter code like TX.")
        return v

    def address(self, prefix=""):
        return {
            "name": self.str(prefix + "name", "Recipient name", max_len=100),
            "street": self.str(prefix + "street", "Street address", max_len=200, min_len=3),
            "city": self.str(prefix + "city", "City", max_len=100),
            "state": self.state(prefix + "state"),
            "zip": self.zip(prefix + "zip"),
        }

    def done(self):
        if self.errors:
            raise Invalid(self.errors)
        return self


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, "Malformed JSON body; expected a JSON object.")
    return data


def old(name, default=""):
    """Template helper: re-fill a form field after a validation redirect."""
    return g.get("old", {}).get(name, default)


# ---------- error handlers ----------

def register_error_handlers(app):
    @app.errorhandler(Invalid)
    def invalid(e):
        if is_api():
            return jsonify(error="validation_failed", fields=e.errors), 400
        for msg in e.errors.values():
            flash(msg, "error")
        session["old"] = {k: v for k, v in request.form.items() if "password" not in k and k != "csrf_token"}
        return redirect(safe_next(_same_site_referrer(), request.path), 303)

    @app.errorhandler(HTTPException)
    def http_error(e):
        if is_api():
            return jsonify(error=e.name.lower().replace(" ", "_"), message=e.description), e.code
        return render_template("error.html", code=e.code, title=e.name, message=e.description), e.code

    @app.errorhandler(Exception)
    def crash(e):
        current_app.logger.exception("Unhandled error")
        db.session.rollback()
        msg = "Something went wrong on our side. It has been logged."
        if is_api():
            return jsonify(error="internal_error", message=msg), 500
        return render_template("error.html", code=500, title="Server error", message=msg), 500


def _same_site_referrer():
    ref = request.referrer or ""
    p = urlparse(ref)
    if p.netloc == request.host:
        return p.path + (f"?{p.query}" if p.query else "")
    return None


# ---------- domain helpers ----------

def audit(action, detail=""):
    db.session.add(AuditLog(actor_id=g.user.id if g.get("user") else None, action=action, detail=detail[:500]))


def money(cents):
    return f"${(cents or 0) / 100:,.2f}"


def take_stock(product_id, qty):
    """Atomic conditional decrement: the DB refuses to oversell even under concurrent checkouts."""
    res = db.session.execute(
        update(Product).where(Product.id == product_id, Product.stock >= qty).values(stock=Product.stock - qty))
    return res.rowcount == 1


# Which transitions each actor may make. Admin override skips this table (but not stock accounting).
TRANSITIONS = {
    "customer": {("pending", "cancelled"), ("delivered", "return_requested")},
    "seller": {("pending", "shipped"), ("pending", "cancelled"), ("shipped", "delivered"),
               ("return_requested", "returned"), ("return_requested", "return_rejected")},
}


def set_item_status(item, new, actor_role, override=False):
    old_status = item.status
    if old_status == new:
        abort(409, f"Item is already {new.replace('_', ' ')}.")
    if not override and (old_status, new) not in TRANSITIONS.get(actor_role, set()):
        abort(409, f"Can't move an item from {old_status.replace('_', ' ')} to {new.replace('_', ' ')}.")
    if old_status not in RESTOCKED and new in RESTOCKED:
        db.session.execute(update(Product).where(Product.id == item.product_id)
                           .values(stock=Product.stock + item.qty))
    elif old_status in RESTOCKED and new not in RESTOCKED and not take_stock(item.product_id, item.qty):
        abort(409, "Not enough stock to reinstate this item.")
    item.status = new


def cart_lines(user):
    return CartItem.query.filter_by(user_id=user.id).join(Product).order_by(CartItem.id).all()


def units_for(lines):
    """Expand (product, qty) pairs into physical units for the UPS packer."""
    units = []
    for p, qty in lines:
        units += [(p.weight_lb, (p.length_in, p.width_in, p.height_in))] * qty
    return units


def shipping_quote(zip_code, lines, residential=True):
    subtotal = sum(p.price_cents * q for p, q in lines)
    try:
        return shipping.quote(zip_code, units_for(lines), setting("fuel_surcharge_pct"), residential,
                              setting("free_shipping_over"), subtotal / 100)
    except shipping.ShippingError as e:
        raise Invalid({"zip": str(e)}) from None


# ---------- uploads ----------

IMAGE_SIGNATURES = {b"\x89PNG\r\n\x1a\n": "png", b"\xff\xd8\xff": "jpg", b"GIF87a": "gif", b"GIF89a": "gif"}


def sniff_image(head):
    for sig, ext in IMAGE_SIGNATURES.items():
        if head.startswith(sig):
            return ext
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def save_upload(file):
    """Validate by content (not filename) and store under a random name. Returns filename or raises Invalid."""
    head = file.stream.read(16)
    file.stream.seek(0)
    ext = sniff_image(head)
    if not ext:
        raise Invalid({"image": "Image must be a PNG, JPEG, GIF, or WebP file."})
    name = f"{uuid.uuid4().hex}.{ext}"
    file.save(Path(current_app.config["UPLOAD_DIR"]) / name)
    return name
