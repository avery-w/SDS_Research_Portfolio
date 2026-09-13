# Marketplace

A full-stack e-commerce marketplace: FastAPI backend, SQLite (SQLAlchemy) for
persistence, and a vanilla HTML/CSS/JS frontend served by the same app.

Three roles: **customer**, **seller**, **admin**.

## Run it

```bash
pip install -r requirements.txt

# optional: seeds a default admin account on first run
export ADMIN_EMAIL=admin@example.com
export ADMIN_PASSWORD=change-me-now

# optional: powers the AI chatbot with real Claude responses.
# without it, the chatbot falls back to a rule-based responder.
export ANTHROPIC_API_KEY=sk-ant-...

# optional: JWT signing key (defaults to a dev key, set this in production)
export MARKETPLACE_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. The database file is `app/marketplace.db`
(created automatically); uploaded product images land in `app/uploads/`.

## Architecture

- `app/models.py` — SQLAlchemy models (users, stores, products, orders, returns, messages, chat history, platform settings).
- `app/schemas.py` — Pydantic request/response schemas (this is what drives the automatic 422 validation errors).
- `app/security.py` — password hashing (stdlib `hashlib.pbkdf2_hmac`, no external crypto dependency) and JWT issuing/verification.
- `app/deps.py` — `get_current_user` / `require_roles(...)` FastAPI dependencies for auth and role checks.
- `app/shipping.py` — the UPS-methodology shipping rate calculator (see below).
- `app/chatbot.py` — the AI shopping assistant.
- `app/routers/` — one router per concern: `auth`, `products` (public browse/search), `sellers` (store/product/inventory/fulfillment), `cart`, `orders` (checkout/history/cancel/returns), `messaging`, `chat`, `admin`.
- `app/static/` — the frontend (`index.html`, `app.js`, `style.css`), a single-page app using `fetch()` against the API. No build step.

## API error conventions

Every endpoint follows the same contract:

- **Invalid input** → `422` with a `detail` string describing what's wrong (from Pydantic validation), or `400` for input that's well-formed but violates a business rule (e.g. insufficient stock, empty cart).
- **Missing/invalid auth** → `401` (no `Authorization: Bearer <token>` header, expired token, malformed token, or a token for a deleted user).
- **Unauthorized** (authenticated but wrong role, or acting on another user's resource) → `403`.
- **Not found** → `404`.

## Shipping rates (UPS methodology)

`app/shipping.py` implements UPS's published *rating methodology*
(dimensional weight, zone-based pricing, service tiers) as a self-contained
calculator, since UPS's live Rating API requires a business developer
account. The origin is fixed at 110 Inner Campus Drive, Austin, TX 78705.
The zone-by-distance estimate uses zip3-prefix delta as a proxy for UPS's
licensed zone chart — see the `ponytail:` comment in that file for the
upgrade path to the real UPS Rating API once credentials are available.

## AI chatbot

Answers general questions (checkout, shipping, returns, account) and is
explicitly instructed to push customers to the in-app "Message Seller"
feature for anything specific to a product or an existing order, since it
has no real visibility into either. Uses the Claude API when
`ANTHROPIC_API_KEY` is set; otherwise a keyword-based responder handles the
same cases so the app works without any external key.

## What's simulated, on purpose

- **Payments**: checkout marks the order `paid` immediately — there's no
  payment gateway wired up. Swap in Stripe/etc. at the `checkout` endpoint
  in `app/routers/orders.py` when needed.
- **Seller messaging** is a simple in-app thread (`SellerMessage` model),
  not email/SMS.
