# Longhorn Market

A multi-seller marketplace built with Flask. Customers browse, buy and message sellers. Sellers run their own store. Admins manage everything and see sales analytics. Checkout quotes UPS shipping from 110 Inner Campus Drive, Austin, TX 78705, and an AI shopping assistant (Claude) helps customers.

## Features

| Role | What they can do |
|---|---|
| Customer | Search/sort/browse, product pages, cart, checkout with live UPS rates, order history, cancel before shipment, request returns after delivery, message sellers about a product or an order, manage profile, address and password |
| Seller | Create/edit store, add/edit/unlist products, inventory, image upload, see and fulfill their own orders (ship with tracking, deliver, approve/deny returns), sales totals, reply to customers |
| Admin | Sales analytics dashboard, manage users (deactivate, change role), stores, products (edit/unlist any), orders (override any status), platform settings (site name, commission, UPS fuel surcharge, assistant on/off) |

A cart with items from two stores becomes two orders, each shipped and fulfilled by its own seller.

## Setup

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then set SECRET_KEY and ANTHROPIC_API_KEY
python -c "import secrets; print(secrets.token_hex(32))"   # paste this as SECRET_KEY
flask --app app init-db
flask --app app create-admin you@example.com   # prompts for a password (10+ chars)
flask --app app run --debug
```

Open http://127.0.0.1:5000, sign up as a seller, open a store and add products, then sign up as a customer in another browser and buy something.

**macOS note:** if the first shipping quote fails with `CERTIFICATE_VERIFY_FAILED`, your python.org Python has no CA certificates yet. Run `/Applications/Python\ 3.x/Install\ Certificates.command` once, or `export SSL_CERT_FILE=$(python -m certifi)`. The first quote downloads the US ZIP code table (via `pgeocode`) and caches it in `~/.cache/pgeocode`.

### Tests

```bash
python test_app.py      # end to end: checkout, stock, authorization, returns, uploads, admin, chatbot validation
python shipping.py      # UPS rate rules self check
```

### Environment variables

| Name | Purpose |
|---|---|
| `SECRET_KEY` | Required. Signs session cookies (the cart lives in the session). |
| `DATABASE_URL` | Defaults to `sqlite:///marketplace.db`. For PostgreSQL: `pip install "psycopg[binary]"` and use `postgresql+psycopg://user:pass@host/db`. |
| `ANTHROPIC_API_KEY` | Needed for the AI assistant. |
| `COOKIE_SECURE` | `1` (default) sends cookies over HTTPS only. Set `0` for local http development. |

### Production checklist

* Run behind HTTPS with `COOKIE_SECURE=1`, using gunicorn (`gunicorn app:app`), PostgreSQL, and a Redis `storage_uri` for Flask-Limiter (`auth.py`) if you run more than one worker. Behind a reverse proxy, wrap the app in `werkzeug.middleware.proxy_fix.ProxyFix` so rate limits see real client IPs.
* **Payments are not wired up.** Orders are placed without charging a card. Add a processor (e.g. Stripe PaymentIntents) at the marked spot in `shop.checkout` before taking real money. Sales tax is also not calculated.
* Shipping uses a UPS rate card approximation (see below). Swap in the UPS Rating API if you need exact negotiated rates.

## Project layout

| File | Contents |
|---|---|
| `app.py` | App setup, security headers, CSRF, CLI commands (`init-db`, `create-admin`) |
| `models.py` | Database models, order status rules, platform settings |
| `auth.py` | Register, login, logout, account, role checks, rate limiter, shared input cleaners |
| `shop.py` | Catalog, search, cart, checkout, shipping rates API, orders, cancel/returns, messaging |
| `seller.py` | Seller dashboard, store, products, image upload |
| `admin.py` | Admin dashboard, analytics, user/store/product/order management, settings |
| `shipping.py` | UPS rate calculation |
| `chatbot.py` | AI shopping assistant endpoint |
| `schema.sql` | PostgreSQL DDL generated from `models.py` (for reference, `init-db` creates the tables) |
| `templates/`, `static/` | Jinja templates, CSS, the one JS file |

## Checkout and shipping API

`POST /api/checkout/rates` with JSON `{"zip": "10001"}` returns rates for the current cart:

```json
{"origin": {"street": "110 Inner Campus Drive", "city": "Austin", "state": "TX", "zip": "78705"},
 "subtotal_cents": 3750,
 "rates": [{"service": "ground", "name": "UPS Ground", "cents": 6986, "total_cents": 10736}, ...]}
```

Send the `X-CSRFToken` header (the page's `<meta name="csrf-token">`). `POST /checkout` recomputes everything server side, so the client never supplies a price.

UPS rules applied in `shipping.py`:

* Dimensions rounded to the nearest inch; dimensional weight = L × W × H / 139, rounded up.
* Billable weight = greater of actual (rounded up) and dimensional weight.
* Limits: 150 lb, 108 in length, 165 in length + girth.
* Zone 2 to 8 from the distance between 78705 and the destination ZIP.
* Services: Ground, 3 Day Select, 2nd Day Air, Next Day Air. Residential surcharge per package, then the admin configurable fuel surcharge.
* Each unit ships as its own package.

## AI assistant

`POST /api/chat` (logged in, 20/min and 200/day per IP) with `{"messages": [{"role": "user", "content": "..."}]}`. It calls `claude-opus-5` at low effort with Anthropic's server side refusal fallback enabled. The system prompt contains a sample of the live catalog and tells the assistant to send customers to the **Message seller** button for product specifics and order issues. It cannot see accounts or orders and has no tools, so it cannot act for anyone. Admins can switch it off in Settings.

## Where user input reaches a query, file path or shell command

No module runs a shell command, and nothing calls `subprocess`, `os.system`, `eval` or `exec`. Every database access goes through the SQLAlchemy ORM or Core expressions, so user values are always bound parameters, never pasted into SQL text. Templates are Jinja with autoescaping on and nothing is marked `|safe`. Every POST (form or JSON) requires a CSRF token.

### auth.py

| Input | Reaches | How it is handled |
|---|---|---|
| register `email`, `name`, `password`, `role` | `select(User).filter_by(email=...)`, `INSERT user` | Bound parameters. Trimmed, length capped, email regex, password 10 to 128 chars and stored as a Werkzeug hash, `role` whitelisted to customer/seller (admins only via CLI). 10 signups/hour/IP. |
| login `email`, `password` | `select(User).filter_by(email=...)` | Bound parameter, length capped. Constant time hash check even for unknown emails. 5 attempts/min/IP. No `?next=` redirect, so no open redirect. Deactivated users are refused and logged out on their next request. |
| account `name`, address, passwords | `UPDATE user` via ORM | Bound. Length caps, `^[A-Z]{2}$` state, `^\d{5}$` ZIP, current password required to change it. |

### shop.py

| Input | Reaches | How it is handled |
|---|---|---|
| search `q` | `lower(name) LIKE ... ESCAPE '/'` | Bound parameter, cut to 100 chars, `contains(..., autoescape=True)` escapes `%` and `_` so input can't act as a wildcard pattern. |
| `sort` | `ORDER BY` | Looked up in a fixed dict, never interpolated. |
| `store`, `page`, product/order/user ids | `WHERE id = ?` | Parsed as `int` by the URL converter or `type=int`. Only active products in active stores of active sellers are visible. |
| cart `qty` | session cookie, then `WHERE id IN (...)` | `int`, clamped to 1 to 99 and to stock. Session is signed, and prices always come from the database. |
| rates API `zip` | `pgeocode` lookup (in memory table, not SQL, not a path) | Must match `^\d{5}$`. Unknown ZIPs rejected. |
| checkout address, `service` | `INSERT order` | Bound. Same address validation as account. `service` whitelisted. Stock taken with an atomic `UPDATE ... WHERE stock >= qty` so it cannot oversell. |
| order `status`, `tracking`, `return_reason` | `UPDATE order` | Caller must own the order, own its store, or be admin (else 404). Status change must be in the role's transition table in `models.py`. Tracking alphanumeric, max 40. |
| message `body`, `product`, `order` | `INSERT message` | Bound, max 2000 chars. Customers may message sellers/admins, and sellers may only reply to people who wrote first. A referenced order must be one the sender is party to. Rendered escaped. |

### seller.py

| Input | Reaches | How it is handled |
|---|---|---|
| store `name`, `description` | `INSERT/UPDATE store` | Bound, length capped, case insensitive uniqueness check. One store per seller (DB unique constraint). |
| product fields | `INSERT/UPDATE product` | Bound. Price parsed as `Decimal` into integer cents, numbers range checked (rejects NaN/inf), DB `CHECK` constraints back it up. Edit requires owning the product's store (or admin), else 404. |
| image upload | **file path** `static/uploads/<name>` | The client filename is never used. Bytes are opened and verified with Pillow, must be JPEG/PNG/WEBP/GIF, and are saved as `<uuid4>.<ext from detected format>`. 5 MB request cap. Served with `X-Content-Type-Options: nosniff`. Flask's static route uses `safe_join`, so a request path cannot leave `static/`. |

### admin.py

| Input | Reaches | How it is handled |
|---|---|---|
| `tab`, `status` filter | template choice, `WHERE status = ?` | Both whitelisted. |
| user/product search `q` | `LIKE ... ESCAPE` | Bound, autoescaped, 100 chars. |
| toggle `kind`, id | `get(Model, id)` | `kind` looked up in a fixed dict of models, id is `int`. Admins cannot deactivate themselves. |
| `role` | `UPDATE user` | Whitelisted to the three roles; admins cannot change their own role. |
| settings | `setting` table | Only known keys are saved. Percentages must be 0 to 100, the assistant flag is coerced to `0`/`1`, other values capped at 200 chars. |

All admin routes require the admin role (403 otherwise).

### shipping.py

No queries, paths or commands. Only the ZIP (validated upstream and again here) goes to the `pgeocode` in memory lookup.

### chatbot.py

| Input | Reaches | How it is handled |
|---|---|---|
| `messages` | Anthropic API (not a query, path or command) | Must be 1 to 20 turns alternating user/assistant, starting and ending with user, each 1 to 2000 chars. Unknown keys are dropped. Login required and rate limited to control cost. |
| seller product names in the catalog sample | system prompt | Truncated and labeled as data. The assistant has no tools and no access to private data, so a prompt injection in a product name can at worst change its wording. Replies are inserted with `textContent`, never as HTML. |

### app.py

The CSP (`default-src 'self'`) forbids inline and third party scripts, which backs up the template escaping. `SECRET_KEY` must come from the environment. `create-admin` takes its email from the CLI operator only and the password via a hidden prompt.
