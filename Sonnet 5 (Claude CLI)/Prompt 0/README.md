# Marketplace

A Flask e-commerce marketplace with three roles: customer, seller, admin.

## Features

- **Customers**: browse/search products, cart, checkout with live UPS shipping
  rates, order history, cancellations, return requests, message sellers, AI
  shopping assistant.
- **Sellers**: manage store profile, products (with image upload) and
  inventory, fulfill their own orders (mark shipped/delivered), message
  customers.
- **Admins**: manage all users/stores/products/orders, deactivate accounts,
  override order status, approve/reject returns, sales analytics dashboard,
  platform settings.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # then edit .env with your keys (see below)
python seed_admin.py admin@example.com yourpassword "Admin Name"
python run.py
```

App runs at http://127.0.0.1:5000 (macOS: if that port is taken by AirPlay
Receiver, run `python -c "from run import app; app.run(port=5050)"` instead,
or disable AirPlay Receiver in System Settings > General > AirDrop & Handoff).

Database is SQLite by default (`db.sqlite3`, auto-created on first run). Set
`DATABASE_URL` in `.env` to point at Postgres/MySQL instead if needed.

## Configuration (.env)

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask session signing key |
| `DATABASE_URL` | SQLAlchemy connection string |
| `UPS_CLIENT_ID` / `UPS_CLIENT_SECRET` / `UPS_ACCOUNT_NUMBER` | UPS Rating API OAuth credentials. Get these from https://developer.ups.com. Ship-from address is fixed to 110 Inner Campus Drive, Austin, TX 78705 per spec. |
| `UPS_ENV` | `test` (CIE sandbox) or `production` |
| `ANTHROPIC_API_KEY` | Powers the AI shopping assistant |

If UPS credentials are not set, checkout falls back to a flat-rate shipping
estimator (still returns Ground/3-Day/2nd Day/Next Day options) so the app
works out of the box. If `ANTHROPIC_API_KEY` is not set, the chatbot falls
back to a simple rule-based responder that still nudges customers to message
the seller.

## Running the self-check

```bash
python test_app.py
```

Covers registration, role-based access control, cart -> shipping rate ->
checkout -> order placement, stock decrement, and order status rollup.

## Project layout

```
app/
  models.py            SQLAlchemy models (User, Store, Product, Order, ...)
  shipping.py           UPS Rating API client + fallback estimator
  chatbot.py             AI assistant (Anthropic API + fallback)
  auth/, customer/, seller/, admin/, api/   Flask blueprints
  templates/             Jinja2 templates (Bootstrap 5 via CDN)
  static/uploads/         Uploaded product images
config.py                 App configuration
run.py                     Entrypoint
seed_admin.py              CLI to create the first admin (no self-registration for admin role)
test_app.py                 Smoke test
```

## Known simplifications

- Payment is simulated at checkout (no real payment gateway integration).
- The shipping estimator (used when UPS credentials aren't configured) uses
  flat weight-tiered rates, not real UPS zone charts.
- Sales analytics are computed live from the database rather than
  precomputed/cached.
