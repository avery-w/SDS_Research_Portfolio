# Marketplace

A full-stack e-commerce marketplace with three roles (customer, seller, admin),
server-rendered with FastAPI + Jinja2 + HTMX-style plain forms, PostgreSQL,
UPS shipping rate quotes, and an Anthropic-powered shopping assistant.

## Stack

- **Backend**: FastAPI (Python), server-rendered Jinja2 templates + Bootstrap 5
- **Database**: PostgreSQL via SQLAlchemy 2.0 + Alembic migrations
- **Auth**: signed session cookies (itsdangerous), bcrypt password hashing, CSRF double-submit tokens
- **Shipping**: UPS Rating API (OAuth2 client-credentials), ship-from fixed at 110 Inner Campus Drive, Austin, TX 78705
- **AI chatbot**: Anthropic Claude, nudges customers to message sellers directly for product/order-specific questions
- **Deployment**: Docker + docker-compose (app + Postgres)

## Project layout

```
app/
  main.py          FastAPI app, middleware, router registration
  config.py        Settings loaded from environment / .env
  database.py      SQLAlchemy engine/session
  models.py        ORM models (users, stores, products, orders, returns, messages, ...)
  security.py      Password hashing, session tokens, CSRF token generation
  deps.py          Auth/role dependencies (require_customer/seller/admin), CSRF check
  routers/         auth, products, cart, checkout, customer, seller, admin, chatbot
  services/
    shipping.py    UPS Rating API integration (with a flat-rate fallback if UPS creds are absent)
    ai_chat.py     Anthropic chat wrapper + system prompt
  utils/uploads.py Validated, re-encoded image uploads for product photos
templates/         Jinja2 HTML templates
static/            CSS + uploaded product images
alembic/           DB migrations
scripts/create_admin.py   CLI to create the first admin account
tests/             pytest unit tests for security/shipping logic
```

## Local setup (Docker, recommended)

1. Copy the env file and fill in secrets:
   ```
   cp .env.example .env
   python -c "import secrets; print(secrets.token_hex(32))"   # paste into SECRET_KEY
   ```
   UPS and Anthropic keys are optional for local dev — checkout falls back to a flat-rate
   shipping estimate and the chatbot returns a static message if they're unset.

2. Start Postgres + the app:
   ```
   docker compose up --build
   ```

3. Run migrations (first time, and after any model change):
   ```
   docker compose exec web alembic revision --autogenerate -m "initial"
   docker compose exec web alembic upgrade head
   ```

4. Create an admin account (admins can't self-register through the public form):
   ```
   docker compose exec web python -m scripts.create_admin admin@example.com "Admin Name"
   ```

5. Visit http://localhost:8000

## Local setup (without Docker)

Requires Python 3.12+ and a running PostgreSQL instance.

```
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit DATABASE_URL to point at your local Postgres
alembic revision --autogenerate -m "initial"
alembic upgrade head
python -m scripts.create_admin admin@example.com "Admin Name"
uvicorn app.main:app --reload
```

## Tests

```
pytest tests/
```

Covers session-token/password security (roundtrip + tampering) and the shipping
rate estimator. These are unit tests for the trickiest logic, not full coverage —
add request-level tests if you extend checkout/auth further.

## Environment variables (`.env`)

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Signs session cookies. Must be a long random value in production. |
| `SESSION_COOKIE_SECURE` | Set `true` in production (HTTPS only). |
| `DATABASE_URL` | SQLAlchemy Postgres URL. |
| `UPS_CLIENT_ID` / `UPS_CLIENT_SECRET` | From https://developer.ups.com — register an app to get these. |
| `UPS_ACCOUNT_NUMBER` | Your UPS shipper account number. |
| `UPS_ENV` | `sandbox` or `production`. |
| `ANTHROPIC_API_KEY` | Powers the AI shopping assistant. |
| `MAX_UPLOAD_MB` | Product image upload size limit. |

## Security notes

- Passwords are hashed with bcrypt (via passlib); sessions are signed, `httponly`,
  `samesite=lax` cookies with a 7-day expiry, not raw guessable IDs.
- All state-changing forms require a CSRF token (double-submit cookie pattern).
- Role checks (`require_customer` / `require_seller` / `require_admin`) gate every
  route; admins can access customer/seller routes too, sellers/customers cannot
  reach admin or each other's seller routes.
- Checkout recomputes price and shipping cost server-side from the database and
  a fresh UPS quote — client-submitted totals are never trusted.
- Uploaded product images are content-validated and re-encoded with Pillow
  (rejects anything that isn't a real JPEG/PNG/WEBP, strips embedded payloads).
- Login and registration are rate-limited per IP (slowapi) to slow credential
  stuffing / spam signups; the chatbot endpoint is rate-limited to cap API cost.
- `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy` headers are
  set on every response.
- **Before going live**: put this behind a TLS-terminating reverse proxy
  (nginx/Caddy/your cloud LB), set `SESSION_COOKIE_SECURE=true`, and run
  `uvicorn`/gunicorn with multiple workers (the Dockerfile already uses
  `--workers 4`). Add a real payment processor (Stripe, etc.) before accepting
  live orders — this app treats checkout as prepaid and has no payment
  integration by design (out of scope for this build).

## Known simplifications (`ponytail:` marked in code)

- Shipping estimates a single combined package using the largest cart item's
  box dimensions rather than real bin-packing. Fine for typical small orders;
  revisit if orders routinely mix many large items.
- No payment gateway: orders are marked `paid` immediately on checkout. Wire in
  Stripe/Braintree before accepting real payments.
