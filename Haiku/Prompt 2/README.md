# Forty Acres Market

A multi-vendor marketplace in Python (Flask + SQLite). It has three roles (customer, seller, admin), a UPS shipping rate API that quotes from 110 Inner Campus Drive, Austin, TX 78705, customer-to-seller messaging, and **Scout**, an AI shopping assistant built on Claude.

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/flask --app app seed          # demo stores, products, 30 days of orders
.venv/bin/flask --app app run           # http://127.0.0.1:5000
```

Every demo account uses the password `demo-pass-123`: `customer@example.com`, `seller@example.com`, `admin@example.com`. Other sellers are `prints@`, `pantry@` and `tech@example.com`, and the other customers are `maria@`, `chris@` and `taylor@example.com`.

For a real deployment, run `flask --app app create-admin` in place of `seed`. Then serve with a WSGI server (for example `gunicorn -w 1 app:app`) behind HTTPS.

| Env var | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Turns on Claude replies for Scout. Without it, Scout answers from built-in rules. |
| `SECRET_KEY` | Session signing key. If unset, one is generated once and stored in `instance/secret_key`. |
| `DATABASE` | SQLite path. Defaults to `instance/market.db`. |
| `SESSION_COOKIE_SECURE=1` | Set this when serving over HTTPS. |

Tests: `.venv/bin/python test_app.py` (pytest also works).

## Layout

| File | What it holds |
|---|---|
| `app.py` | All routes, auth, validation and the error contract |
| `db.py` | SQLite schema, connection and settings |
| `shipping.py` | UPS rate engine (zones, dimensional weight, surcharges, packing) |
| `chatbot.py` | Scout: Claude (`claude-opus-5`) with a rule-based fallback |
| `seed.py` | Demo data |
| `templates/`, `static/` | Jinja pages, CSS (light and dark), and one JS file for checkout and chat |

## Features by role

- **Customers** can browse and search with filters, sorting and paging, and open store pages. They manage a cart that can hold items from several stores. Checkout shows live UPS quotes with arrival dates and creates one order per store. Customers can see their order history and timeline, cancel an order before it ships, and request a return within the return window. They can also message sellers and edit their profile, address and password, or close their account.
- **Sellers** get a dashboard with 30-day sales, estimated payout, orders to ship and return requests. They can create and edit products, upload images, edit stock inline, hide or publish listings, and edit their store profile. They fulfill orders by marking them shipped (with a UPS `1Z` tracking number) and delivered, approve or reject returns, and use a messaging inbox.
- **Admins** have an analytics page showing GMV per day, KPIs, orders by status, sales by category, and top stores and products. They manage users (activate, deactivate, change role), stores, products (edit or deactivate any of them) and orders (override any status, with a logged reason). They also edit platform settings (tax, fuel surcharge, residential surcharge, free Ground threshold, return window, platform fee, site banner), can read any conversation, and have a full activity log.

## Shipping (UPS rules)

`POST /api/shipping/rates` follows UPS rating rules:
- It enforces the limits of 150 lb, 108 in on the longest side and 165 in of length plus girth. Sellers can't list an item that breaks them.
- Dimensional weight is L×W×H / 139, with dimensions rounded up to whole inches. Billable weight is the higher of actual and dimensional weight, rounded up to the next pound.
- The zone (2 to 8) comes from the distance between Austin and the destination ZIP3. Texas ZIP3s are resolved by region.
- Additional Handling applies when the longest side is over 48 in, the second-longest is over 30 in, or the package weighs over 50 lb. Large Package applies when length plus girth is over 130 in or the longest side is over 96 in, with a 90 lb minimum billable weight.
- Residential and fuel surcharges are applied, and both are set in admin settings.
- Services are Ground, 3 Day Select, 2nd Day Air and Next Day Air. Arrival dates skip weekends. Alaska and Hawaii get air services only.
- A multi-item order is split into several boxes whenever one box would exceed the UPS limits.

The base rate table approximates UPS published daily rates. To use contract rates, replace `GROUND_BASE` and `GROUND_PER_LB` or call the UPS Rating API.

## Error contract

These rules hold on every route:

| Situation | JSON API (`/api/*`) | HTML pages |
|---|---|---|
| Invalid input | `400 {"error"}` | POST: flash the message and redirect back. GET: 400 page |
| Missing auth | `401 {"error"}` | Redirect to `/login?next=…` |
| Wrong role, or not the owner | `403 {"error"}` | 403 page |
| Unknown id | `404` | 404 page |
| Conflict (stock ran out, illegal status change, return window closed) | `409` | 409 page |
| Body isn't JSON | `415` | n/a |
| Too many requests (10 failed logins or 20 chat messages per window) | `429` | 429 page |
| Upload over 5 MB | `413` | 413 page |

HTML forms need a CSRF token; a missing or wrong token returns 400. JSON APIs are exempt only when the request has `Content-Type: application/json`, which a cross-site form cannot send.

### Endpoints

| Endpoint | Auth | Invalid input (400) | Missing auth | Unauthorized (403) / other |
|---|---|---|---|---|
| `GET /` `?q,category,min,max,sort,page,store` | public | unknown category or sort, bad numbers, page out of 1..1000 | n/a | 404 for an unknown or closed store |
| `GET /products/<id>` | public | n/a | n/a | 404 if the product is missing or hidden (the owner and admins can still see it) |
| `GET/POST /register` | guest | bad email, password under 8 chars, role not customer/seller, duplicate email or store name | n/a | signed-in users are redirected |
| `GET/POST /login` | guest | missing fields, wrong credentials, deactivated account | n/a | 429 after 10 failures in 5 min |
| `POST /logout` | any | n/a | n/a | n/a |
| `GET/POST /account` | signed in | bad state or ZIP, name missing | redirect to login | n/a |
| `POST /account/password` | signed in | wrong current password, new password under 8 | redirect to login | n/a |
| `POST /account/close` | customer, seller | wrong password | redirect to login | admins get 403 |
| `GET /cart`, `POST /cart/add`, `POST /cart/update` | customer | non-integer or out-of-range qty, more than in stock | redirect to login | other roles get 403. 404 for an unknown product or one not in the cart |
| `POST /api/shipping/rates` `{zip, items?}` | public with `items`, customer for the cart | bad ZIP, unsupported ZIP (PO/military/territories), malformed `items`, unavailable product, empty cart | 401 when quoting the cart without signing in | 403 when a non-customer quotes a cart. 415 if the body isn't JSON |
| `POST /api/checkout` `{service,name,street,city,state,zip,save_address?}` | customer | unknown service, bad address, empty cart, service not available to that state | 401 | 403 for other roles. 409 if stock changed or ran out |
| `GET /orders` | customer | n/a | redirect to login | 403 for other roles |
| `GET /orders/<id>` | the customer, the store's seller, admin | n/a | redirect to login | 403 for anyone else, 404 if the order is missing |
| `POST /orders/<id>/status` | same as above | unknown status, bad tracking number, missing return reason | redirect to login | 403 if this role can't make the change (e.g. a customer marking it shipped). 409 for an illegal status change or a closed return window. Admins can set any status |
| `GET /messages`, `GET/POST /messages/<id>` | signed in | empty body or over 2000 chars | redirect to login | 403 if you aren't in the conversation (admins can read and reply to any). 404 if it's missing |
| `POST /messages/start` | customer | product not in that store, empty body | redirect to login | 403 for other roles or someone else's order. 404 for an unknown or closed store |
| `POST /api/chat` `{messages:[…]}` | public or customer | not a list, over 20 turns, roles not alternating, content not 1..2000 chars | n/a | 403 for sellers and admins, 429 if rate limited, 415 if not JSON |
| `GET /seller`, `POST /seller/store` | seller | unknown status filter, store name taken | redirect to login | 403 for other roles |
| `GET/POST /seller/products/new` | seller | invalid fields, price with more than 2 decimals, item over UPS limits, image not PNG/JPEG/GIF/WebP | redirect to login | 403 for admins (only sellers create products) |
| `GET/POST /seller/products/<id>/edit`, `POST …/stock`, `POST …/toggle` | owning seller, admin | same as above, and stock must be 0..100000 | redirect to login | 403 for other sellers, 404 if the product is missing |
| `GET /admin?tab=…` | admin | bad status filter | redirect to login | 403 for non-admins, 404 for an unknown tab |
| `POST /admin/users/<id>` | admin | unknown action or role, acting on your own account | redirect to login | 403, and 404 for an unknown user |
| `POST /admin/stores/<id>` | admin | unknown action | redirect to login | 403, and 404 for an unknown store |
| `POST /admin/settings` | admin | any value out of range | redirect to login | 403 |
| `GET /healthz` | public | n/a | n/a | n/a |

## Known limits

- Payment is simulated and no card data is collected. Plug in a provider such as Stripe inside `api_checkout` before the commit.
- The rate limiter runs in memory, so it works per process. Move it to Redis if you run more than one worker.
- SQLite in WAL mode is fine for a single server. Use Postgres if you need to scale horizontally.
