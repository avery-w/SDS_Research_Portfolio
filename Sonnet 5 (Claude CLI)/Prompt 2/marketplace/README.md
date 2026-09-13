# Marketplace

Full-stack e-commerce marketplace (Flask + SQLite) with customer, seller, and
admin roles.

## Setup

```bash
cd marketplace
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# creates tables + seeds an admin account
ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=changeme123 python init_db.py

python run.py                  # http://127.0.0.1:5000
```

Set `SECRET_KEY` and `DATABASE_URL` env vars for anything beyond local dev
(defaults are dev-only, see `config.py`). To use Postgres/MySQL instead of
SQLite, just point `DATABASE_URL` at it (SQLAlchemy handles the rest).

Run the shipping calculator self-check:

```bash
python tests/test_shipping.py    # or: python -m pytest tests/
```

## Roles

- **Customer**: browse/search products, cart, checkout, order history,
  cancel orders, request returns, message sellers, ask the chatbot.
- **Seller**: register (role=seller) then set up a store, list/edit
  products with image uploads, manage inventory, view/fulfill orders,
  approve returns.
- **Admin**: log in with the seeded admin account, see `/admin` for user
  and store management (deactivate/reactivate), order status overrides,
  sales analytics, and platform key/value settings.

Sign-up only lets you pick `customer` or `seller` — admin accounts are
created via `init_db.py` (or promoted directly in the DB), never through the
public form.

## Shipping API

`POST /api/checkout/shipping-rate` with JSON `{"zip": "10001", "weight_lbs": 2, "service": "ground"}`.
Origin is fixed at 110 Inner Campus Drive, Austin, TX 78705. Rate is modeled
on UPS's published zone/weight rate structure (Ground / 3 Day Select / 2nd
Day Air / Next Day Air), but zone lookup is a distance-from-zip-prefix
heuristic rather than UPS's proprietary zone chart, since that requires a UPS
developer account. See the docstring in `app/shipping.py` for how to swap in
the real UPS Rating API.

## AI chatbot

`POST /api/chatbot/ask` (login required) with JSON `{"message": "..."}`.
Rule-based FAQ + order-status lookups for the logged-in customer's own
orders; anything product/order-specific redirects the customer to the
in-app "Message Seller" feature instead of guessing. Swap `app/chatbot.py`
for a real LLM call if you want open-ended conversation.

## Data model

See `app/models.py`: `User`, `Store`, `Product`, `ProductImage`, `CartItem`,
`Order`, `OrderItem`, `Message`, `PlatformSetting`. Tables are created
automatically on first run via `db.create_all()` (SQLite dev setup) — no
separate migration tool for a project this size; add Alembic if you need
real migrations later.

## Security notes: where user input reaches a query, file path, or command

No code in this app shells out (`subprocess`, `os.system`, etc.), so there is
no shell-injection surface at all.

- **All database queries** (`auth.py`, `customer.py`, `seller.py`,
  `admin.py`, `chatbot.py`) go through the SQLAlchemy ORM
  (`Model.query.filter_by(...)`, `db.session.get(...)`). User input is
  always passed as a bound parameter, never string-formatted into SQL — this
  includes the product search box (`Product.name.ilike(f"%{q}%")`, where `q`
  is still bound as a parameter by SQLAlchemy, not concatenated into raw
  SQL).
- **Access control on every ID-based query**: cart items, orders, order
  items, and seller products are always filtered by `customer_id`/`store_id`
  matching the logged-in user, so one user can't read or mutate another's
  data by guessing an ID (IDOR).
- **File paths** (`seller.py: _save_uploaded_images`): uploaded filenames go
  through `werkzeug.utils.secure_filename` and get a random `uuid4` prefix
  before being joined to the fixed `UPLOAD_FOLDER`, so a crafted filename
  (e.g. `../../etc/passwd`) can't escape the uploads directory or collide
  with another file. Extension is checked against an allowlist
  (`ALLOWED_IMAGE_EXTENSIONS`) before saving, and `MAX_CONTENT_LENGTH` caps
  upload size.
- **Shipping API** (`shipping.py`): zip/weight/service from the request body
  are type-coerced (`float()`, digit-stripping) and validated before use;
  they only ever index into an in-memory rate table, never a query or path.
- **Chatbot API** (`chatbot.py`): free-text `message` is only pattern
  matched against a fixed keyword list, never interpolated into a query;
  `order_id` is coerced to `int` and the resulting DB lookup is scoped to
  `current_user.id`.
- **CSRF**: all state-changing HTML forms carry a Flask-WTF CSRF token; the
  two JSON APIs (`shipping-rate`, `chatbot/ask`) are exempted since neither
  mutates another user's data.
- **Passwords**: hashed with Werkzeug's `generate_password_hash`
  (PBKDF2-SHA256 by default), never stored or logged in plaintext.
- **Output escaping**: all HTML rendering goes through Jinja2's autoescaping
  (on by default for `.html` templates); the chatbot widget's JS uses
  `textContent`, not `innerHTML`, when inserting chat messages, to avoid
  DOM-based XSS from pasted text.
