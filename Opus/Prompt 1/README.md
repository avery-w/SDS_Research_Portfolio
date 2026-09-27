# Longhorn Market

A multi-vendor e-commerce marketplace built with Flask. Customers shop across many independent stores,
sellers run their own storefronts, and admins manage the whole platform. Checkout prices shipping with
UPS rules from a fixed origin (110 Inner Campus Drive, Austin, TX 78705), and a Claude-powered assistant
helps shoppers and steers product and order questions to the seller.

## Features

**Customers**: browse, search, filter by category and price, sort; cart; checkout with live UPS rates;
order history; cancel before shipment; request returns after shipment; account and saved address;
direct messages with sellers; AI shopping assistant.

**Sellers**: create and edit a store; add and edit products with images, stock, and package dimensions;
low stock alerts; fulfill orders (ship with tracking number, mark delivered, cancel); approve or reject
returns; sales dashboard with a 30-day revenue chart; message customers.

**Admins**: sales analytics (gross sales, commission, orders, average order, units, 30-day chart, top
products, top stores, orders by status, user counts); manage users (change role, deactivate); manage
stores (rename, deactivate); edit or hide any product; override any order's status; platform settings
(site name, commission rate, announcement banner).

Deactivating a user blocks login and ends their current session. Deactivating a seller or their store
hides all their listings from the shop.

## Setup

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then set SECRET_KEY, and optionally ANTHROPIC_API_KEY and UPS_* keys
flask --app marketplace init-db --seed
flask --app marketplace run
```

Open http://127.0.0.1:5000. With `--seed`, these demo accounts exist (password `password123`):

| Role | Email |
|---|---|
| Admin | admin@example.com |
| Seller | seller@example.com |
| Customer | customer@example.com |

Create a real admin with `flask --app marketplace create-admin you@example.com "Your Name"`.

### Production

```bash
export SECRET_KEY=... SESSION_COOKIE_SECURE=1 DATABASE_URL=postgresql+psycopg://user:pass@host/db
pip install "psycopg[binary]"
flask --app marketplace init-db
gunicorn -w 4 "marketplace:create_app()"
```

Serve `marketplace/static/uploads` from persistent storage, since product images are saved there.

## Configuration

All settings are environment variables (see `.env.example`).

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Signs sessions and CSRF tokens. Required in production. |
| `DATABASE_URL` | SQLAlchemy URL. Defaults to SQLite at `instance/marketplace.db`. |
| `SESSION_COOKIE_SECURE` | Set to `1` behind HTTPS. |
| `ANTHROPIC_API_KEY` | Enables the Claude assistant. Without it, the assistant answers from the product database. |
| `CHAT_MODEL` | Claude model for the assistant, default `claude-opus-5`. |
| `UPS_CLIENT_ID`, `UPS_CLIENT_SECRET`, `UPS_ACCOUNT_NUMBER` | Enable live UPS Rating API quotes. |
| `UPS_BASE_URL` | `https://wwwcie.ups.com` (UPS test) or `https://onlinetools.ups.com` (production). |
| `UPS_API_VERSION` | Rating API version path segment, default `v2409`. |

## Shipping API

All shipments originate at **110 Inner Campus Drive, Austin, TX 78705**. Each store's items ship as a
separate package set, so a cart with two stores gets two shipments and two orders.

`POST /api/shipping/rates` (logged in, rates the current cart)

```json
{"street": "350 5th Ave", "city": "New York", "state": "NY", "zip": "10118"}
```

```json
{
  "source": "estimate",
  "origin": "110 Inner Campus Drive, Austin, TX 78705",
  "services": [
    {"code": "03", "name": "UPS Ground", "amount_cents": 2526, "business_days": 4, "per_shipment_cents": [2526]}
  ]
}
```

`POST /api/checkout` takes the address plus `name` and `service_code`, recomputes rates on the server,
reserves stock atomically, creates one order per store, and empties the cart. It returns `201` with
`order_ids`, `total_cents`, and `redirect`.

Both endpoints are CSRF protected: send the page's `csrf-token` meta value as the `X-CSRFToken` header.

**How rates are computed.** With UPS credentials set, rates come from the UPS Rating API (`Shop`
request, negotiated rates when your account has them). Without credentials, or if UPS is unreachable,
the app estimates using UPS guidelines:

- Billable weight is the greater of the actual weight and the dimensional weight (L × W × H / 139),
  each rounded up to the next pound.
- Packages over 150 lb, longer than 108 in, or over 165 in length plus girth are rejected.
- Large packages (over 96 in long or over 130 in length plus girth) bill at least 90 lb plus a surcharge.
- Additional handling applies over 50 lb, a side over 48 in, or a second side over 30 in.
- Residential and fuel surcharges are added.
- Zones 2 to 8 come from distance between Austin and the destination state.

The estimator's rate table approximates UPS daily list rates and uses state-level zones, and it covers
the contiguous US only. Use the live API for exact prices and for Alaska and Hawaii.

## AI assistant

The chat bubble (bottom right, logged-in users) calls `POST /api/chat` with the conversation. The
server searches the catalog for products matching the question, adds the customer's recent orders,
and asks Claude to answer. The reply comes back with "Message seller" links, and the assistant is told
to send questions it can't answer from the listing (sizing, materials, order specifics) to the seller
through the built-in messaging. The request uses server-side refusal fallbacks
(`server-side-fallback-2026-07-01`). Seller-written listing text is passed as data, not instructions.

## Project layout

```
marketplace/
  __init__.py     app factory, login, CSRF, CLI commands (init-db, create-admin)
  models.py       database models, order status rules, sales analytics query
  auth.py         register, login, logout, role_required decorator
  shop.py         customer pages: catalog, cart, checkout page, orders, account, messages
  seller.py       seller dashboard, products and image uploads, order fulfillment
  admin.py        analytics, users, stores, products, order overrides, settings
  api.py          JSON API: shipping rates, checkout, chat
  shipping.py     UPS Rating API client and UPS-guideline estimator
  chatbot.py      Claude assistant
  seed.py         demo data
  templates/      Jinja templates
  static/         CSS, JS, uploaded images
schema.sql        database schema (PostgreSQL DDL, generated from models.py)
tests/test_app.py UPS rule checks and an end-to-end flow across all three roles
```

## Tests

```bash
python tests/test_app.py        # or: pip install pytest && pytest tests
```

## Not included

- **Payments.** Checkout places orders without charging a card. Add a payment provider (for example
  Stripe Checkout) in `api.checkout` before creating orders.
- **Email notifications** and **rate limiting** on login and chat. Add them before going public.
- **Database migrations.** `init-db` creates tables. Add Flask-Migrate once the schema starts changing
  in production.
