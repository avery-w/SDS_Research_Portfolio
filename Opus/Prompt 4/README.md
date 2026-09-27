# Marketplace

A multi-seller e-commerce marketplace built with Django 6.1, PostgreSQL, and Caddy. It has customer, seller, and admin roles, UPS shipping rates, and a Claude-powered shopping assistant.

## Features

**Customers** browse and search products, manage their account and password, keep a cart, check out with UPS shipping, view order history, cancel orders that haven't shipped, request returns, and message sellers.

**Sellers** create and edit their store, add and edit products (price, stock, weight, dimensions), upload product images, see sales totals, and fulfill orders: ship with a tracking number, mark delivered, cancel, and approve or deny returns. Stock is restored on cancellation and approved returns.

**Admins** (role `admin`) get:
- the Django admin at `/$DJANGO_ADMIN_URL`, where they manage users, stores, products, orders, messages, and site settings. They can deactivate or activate users, stores, and products, and force any order status (cancelling or returning an order restocks it).
- the analytics dashboard at `/staff/analytics/`: GMV, shipping, commission, daily sales for the last 30 days, top products, top sellers, orders by status, and users by role.

**Site settings** (a singleton in the admin): site name, commission percent, whether sellers can sign up, and whether the chatbot is on.

**Shipping API.** `POST /api/shipping/rates/` takes JSON `{line1, city, state, zip}` and returns UPS Ground, 3 Day Select, 2nd Day Air, and Next Day Air rates for the current cart. Every shipment starts at **110 Inner Campus Drive, Austin, TX 78705**, and each seller's items ship as a separate shipment.
- If `UPS_CLIENT_ID` is set, rates come from the live UPS Rating API (OAuth, `/api/rating/v2409/Shop`).
- Otherwise a built-in estimator applies UPS rules: dimensional weight (L×W×H / 139), billing rounded up to the whole pound, the 150 lb / 108 in / 165 in length+girth package limits, zone by destination, residential and additional-handling surcharges, and the fuel surcharge.
- Checkout recomputes shipping on the server and never trusts prices sent by the client.

**AI assistant.** A chat widget for logged-in users, backed by Claude (`claude-opus-5` by default, with server-side refusal fallbacks). It sees the catalog items that match the question and the customer's own recent orders. It has no tools and cannot change anything. It is instructed to send customers to **Message seller** for product and order specifics, and that button appears on every product and order page.

## Quick start (local)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_DEBUG=1 ANTHROPIC_API_KEY=sk-ant-...   # chat works without a key but replies "unavailable"
python manage.py migrate && python manage.py createcachetable
python manage.py createsuperuser        # becomes role=admin
python manage.py runserver
```

Local runs use SQLite. The admin is at http://localhost:8000/manage/. Run the tests with `DJANGO_DEBUG=1 python manage.py test shop`.

## Production deploy (Docker Compose)

```bash
cp .env.example .env        # set DOMAIN, DJANGO_SECRET_KEY, POSTGRES_PASSWORD, DJANGO_ADMIN_URL, API keys
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```

Point DNS for `$DOMAIN` at the host. Caddy gets TLS certificates automatically, serves `/static` and `/media`, and proxies everything else to gunicorn. On every start the web container runs migrations, creates the cache table, and collects static files.

Services: `db` (Postgres 17), `web` (gunicorn, non-root), `caddy` (ports 80/443). Only Caddy is exposed.

## Database schema

The Django migrations in `shop/migrations/` are authoritative. `schema.sql` is the same schema rendered as PostgreSQL DDL for reference.

| Table | Purpose |
|---|---|
| `shop_user` | Accounts, with `role` of customer, seller, or admin. `is_active=false` deactivates. |
| `shop_store` | One store per seller |
| `shop_product`, `shop_productimage` | Listings: price, stock, weight/dimensions for shipping, images |
| `shop_cartitem` | Persistent cart, one row per user+product |
| `shop_order`, `shop_orderitem` | One order per seller per checkout. Items snapshot the name and price. |
| `shop_message` | Direct messages between customers and sellers, optionally about a product or order |
| `shop_sitesettings` | Platform settings |

## Security

- HTTPS only: HSTS, secure/HttpOnly/SameSite cookies, SSL redirect.
- Strict CSP with no inline scripts or styles, `X-Frame-Options: DENY`, nosniff, and a same-origin referrer policy.
- CSRF on every form and on the JSON APIs.
- Passwords use Django PBKDF2 with a 10-character minimum and common and numeric password checks.
- Rate limits on login (per IP and per username), signup, chat, messaging, and the shipping API.
- Every seller and customer query is scoped to its owner. Other users' orders and products return 404, not 403.
- Order status changes are atomic conditional updates, so double submits can't double restock. Checkout locks product rows and re-checks stock inside a transaction.
- Uploads accept JPEG, PNG, or WebP only. They are verified by Pillow, limited to 5 MB, and stored under random names. Caddy serves them with `nosniff` and `CSP: sandbox`.
- Admins sign in at a secret URL, and signup can't create admins.
- The chatbot is read-only, and seller text is marked as untrusted in its prompt. Replies are rendered as text, never HTML.

## Known limits

- **No payment processing.** Orders are placed without taking money. Add Stripe Checkout, marking orders paid from its webhook, before going live.
- The shipping estimator's zone table is regional and approximate. Configure UPS credentials to get real rates.
- Rate limiting trusts `X-Forwarded-For` from Caddy. Don't expose gunicorn directly.
- Search uses `icontains`. Switch to Postgres full-text search if the catalog gets large.
