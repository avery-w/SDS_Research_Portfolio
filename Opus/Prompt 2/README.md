# Longhorn Market

A multi-seller e-commerce marketplace built with Flask, SQLAlchemy and SQLite. It has three roles
(customer, seller, admin), live UPS shipping rates from **110 Inner Campus Drive, Austin, TX 78705**,
in-app customer-to-seller messaging, and a Claude-powered shopping assistant.

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/flask --app app seed          # creates instance/market.db with demo data
.venv/bin/flask --app app run --debug   # http://127.0.0.1:5000
.venv/bin/python test_app.py            # end-to-end contract checks
.venv/bin/python shipping.py            # UPS rating self-checks
```

Demo logins all use the password `password123`:

| Role | Email |
| --- | --- |
| Admin | admin@longhorn.market |
| Seller | seller1@longhorn.market, seller2@…, seller3@… |
| Customer | customer@longhorn.market, sam@…, taylor@… |

### Configuration (environment variables)

| Variable | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | random, saved to `instance/secret_key` | Session signing. Set this in production. |
| `DATABASE_URL` | `sqlite:///instance/market.db` | Any SQLAlchemy URL (e.g. Postgres). |
| `UPLOAD_DIR` | `instance/uploads` | Product image storage. |
| `SESSION_COOKIE_SECURE` | off | Set to `1` behind HTTPS. |
| `ANTHROPIC_API_KEY` | none | Enables the Claude assistant. Without it the bot falls back to keyword search. |
| `CHAT_MODEL` | `claude-opus-5` | Model the assistant uses. |
| `CHATBOT_OFFLINE` | off | Set to `1` to force the offline assistant. |

Admins can change runtime settings at `/admin/settings`: tax rate, commission, UPS fuel surcharge,
free-shipping threshold, return window, announcement banner and seller sign-ups.

## Features

- **Customers** can browse, search, filter and sort products. They also manage their cart, check out
  with live UPS rates, view order history, cancel orders that haven't shipped, request returns within
  the return window, manage their profile, address and password, deactivate their own account, and
  message sellers.
- **Sellers** can set up their store, create and edit products, upload images (checked by content, 5 MB max),
  adjust inventory inline, list or unlist products, ship items with UPS tracking numbers, mark items delivered,
  approve or reject returns, see sales analytics (30-day chart, payout after commission, top products,
  low stock), and reply to customers.
- **Admins** get a platform analytics dashboard (GMV, commission, AOV, daily chart, top stores and products,
  revenue by category, item status mix). They can manage users (create, change role, deactivate or reactivate),
  suspend stores, take down listings (sellers can't re-list them), force-cancel orders, override any item status,
  reply in any conversation, edit platform settings, and read the audit log of every admin action.
- **Bevo Bot** (`/api/chat`, the floating widget) runs Claude with tools that search the catalog, fetch products,
  estimate UPS shipping, and read the signed-in customer's orders. Its `contact_seller` tool adds a
  "Message seller" button, and the bot is prompted to hand off product and order specifics to the seller.
  Server-side refusal fallbacks (`fallbacks: "default"`) are enabled.

### UPS shipping (`shipping.py`)

Every shipment originates from 110 Inner Campus Drive, Austin, TX 78705. Rating follows UPS rules:

- Zones 2 to 8 come from the distance between the origin and the destination ZIP3 region. AK and HI get air services only.
- Dimensional weight is L×W×H ÷ 139 with dimensions rounded to whole inches. Billable weight is the greater of actual and dimensional weight, rounded up to the next pound.
- Hard limits: 150 lb, 108 in length, 165 in length + girth.
- Additional Handling applies when the longest side is over 48 in, the second side is over 30 in, or the package is over 50 lb.
- Large Package applies over 130 in length + girth, with a 90 lb minimum billable weight.
- Residential surcharge, plus a fuel surcharge percentage set by the admin.
- Cart items are packed into stock cartons by volume, and each carton holds at most 150 lb.
- Services: Ground, 3 Day Select, 2nd Day Air, Next Day Air.

The rate card approximates UPS daily rates. To use negotiated rates, swap `quote()` for a call to the
UPS Rating API. The inputs and outputs stay the same.

## Error contract

Every route goes through `core.py`, so the same rules hold everywhere:

| Situation | HTML pages | JSON API (`/api/*`) |
| --- | --- | --- |
| Not signed in | `302` to `/login?next=…` | `401 {"error":"unauthorized"}` |
| Signed in with the wrong role | `403` page | `403 {"error":"forbidden"}` |
| Record belongs to someone else | `404` (existence is never revealed) | `404` |
| Invalid input | `303` back to the form, errors flashed, input kept (except passwords) | `400 {"error":"validation_failed","fields":{field: message}}` |
| Malformed JSON / wrong content type | – | `400` / `415` |
| Missing or wrong CSRF token | `400` page | not used, because writes must be JSON (`415` otherwise), which browsers can't send cross-site |
| Invalid state change, out of stock, empty cart | `409` page | `409 {"error":"conflict","message":…}` |
| Upload over 5 MB | `413` | `413` |
| Rate limited (login 10/5 min, register 10/h, chat 20/min) | `429` | `429` |
| Deactivated account | signed out on the next request. Login returns `403` | `401` |
| Unexpected crash | `500` page, logged, transaction rolled back | `500 {"error":"internal_error"}` |

Browsing pages (`/products`, `/stores/<slug>`, admin list filters) are lenient. Unparseable filters fall back
to their defaults instead of erroring. The API equivalents validate strictly and return `400`.

## Endpoints

"Customer", "Seller" and "Admin" mean the route requires that role. "Signed in" means any role.
Every POST form also requires the CSRF token.

### Public and auth

| Method & path | Auth | Invalid input | Other errors |
| --- | --- | --- | --- |
| `GET /`, `GET /products`, `GET /products/<id>`, `GET /stores/<slug>` | none | filters fall back to defaults | `404` if the product or store is inactive or missing |
| `GET/POST /register` | none (signed-in users are redirected) | `303` back: name, email format and uniqueness, password ≥ 8, role | seller role rejected when seller sign-up is disabled; `429` |
| `GET/POST /login` | none | – | `401` for bad credentials, `403` for a deactivated account, `429`; unsafe `next` URLs ignored |
| `POST /logout` | none | – | – |
| `GET /uploads/<name>` | none | – | `404` |

### Customer

| Method & path | Auth | Invalid input | Other errors |
| --- | --- | --- | --- |
| `GET/POST /account`, `POST /account/password` | Signed in | `303` back (email taken, bad ZIP/state, wrong current password) | – |
| `POST /account/deactivate` | Customer, Seller | wrong password → `303` back | admins are `403` |
| `GET /cart`, `POST /cart/add`, `POST /cart/<pid>` | Customer | qty 0 to 99, product id | `404` unknown or unavailable product, `409` over stock |
| `GET/POST /checkout` | Customer | address and service → `303` back | `409` empty cart, unavailable item, or sold out mid-checkout (nothing is charged or reserved) |
| `GET /orders` | Customer | – | – |
| `GET /orders/<id>` | Signed in | – | `404` unless it's the owner, a seller with items on the order (who sees only their own lines), or an admin |
| `POST /orders/<id>/cancel` | Customer | – | `404` not yours, `409` once any item has shipped |
| `POST /order-items/<id>/<status>` | Customer, Seller | reason (return) or tracking `1Z…` (ship) → `303` back | `404` not yours; `409` for a disallowed transition or a closed return window |
| `GET /messages`, `GET/POST /messages/<id>` | Signed in | body 1 to 4000 chars | `404` unless you're a participant or an admin |
| `GET/POST /messages/new` | Customer | `store_id` required; the product must belong to the store and the order must be yours and include that store | `404` inactive store |

Allowed item transitions: the customer can go `pending→cancelled` and `delivered→return_requested`. The seller
can go `pending→shipped|cancelled`, `shipped→delivered`, and `return_requested→returned|return_rejected`.
Admins can override any transition. Stock is restored whenever an item enters `cancelled` or `returned`,
and taken again (or `409`) when it leaves them.

### Seller (`/seller/*`)

| Method & path | Invalid input | Other errors |
| --- | --- | --- |
| `GET /seller` | – | redirects to store setup if the seller has no store |
| `GET/POST /seller/store` | name 2 to 80 chars → `303` back | `403` while suspended |
| `GET /seller/products`, `GET/POST /seller/products/new`, `GET/POST /seller/products/<id>/edit` | price, stock, weight and dimensions ranges; image must be PNG/JPEG/GIF/WebP by content | `409` no store, `404` another seller's product, `403` suspended store, `413` image too large |
| `POST /seller/products/<id>/stock` | stock 0 to 100000 | `404`, `403` |
| `POST /seller/products/<id>/toggle` | – | `404`; `403` when an admin took the listing down |
| `GET /seller/orders` | an unknown status filter is ignored | `409` no store |

Every seller route returns `302` to login when signed out and `403` for other roles.

### Admin (`/admin/*`, guarded as a blueprint: `302` to login when signed out, `403` for other roles)

| Method & path | Invalid input | Other errors |
| --- | --- | --- |
| `GET /admin` (analytics) | – | – |
| `GET /admin/users`, `POST /admin/users/new` | email, password and role validation → `303` back | – |
| `POST /admin/users/<id>` | `action` ∈ activate/deactivate/set_role | `404`; `409` acting on yourself or demoting a store owner to customer |
| `GET /admin/stores`, `POST /admin/stores/<id>/toggle` | – | `404` |
| `GET /admin/products`, `POST /admin/products/<id>/toggle` | – | `404` |
| `GET /admin/orders`, `POST /admin/orders/<id>/cancel` | – | `404`; `409` if nothing is left to cancel |
| `POST /admin/order-items/<id>/status` | status must be valid | `404`; `409` when there isn't enough stock to reinstate the item |
| `GET/POST /admin/settings` | typed and range-checked per setting → `303` back | – |
| `GET /admin/audit` | – | – |

### JSON API

| Method & path | Auth | Notes |
| --- | --- | --- |
| `GET /api/health` | none | DB ping |
| `GET /api/products?q&category&min_price&max_price&sort&page&per_page` | none | strict `400` on bad params, `per_page` ≤ 50 |
| `GET /api/products/<id>` | none | `404` if unavailable |
| `GET /api/cart` · `POST /api/cart` · `PATCH /api/cart/<pid>` · `DELETE /api/cart/<pid>` | Customer | `201` on add; `404` unknown line; `409` over stock; `qty: 0` removes the line |
| `POST /api/shipping/rates` | none with `items`; Customer without them (uses the cart) | `{zip, residential?, items?:[{product_id, qty}]}`. `400` for a bad ZIP or items, `401`/`403` when `items` is omitted and there's no customer session, `409` empty cart |
| `POST /api/checkout` | Customer | `{name, street, city, state, zip, service: GND/3DS/2DA/1DA}` → `201` order. `400` / `409` as above |
| `GET /api/orders` | Customer | – |
| `GET /api/orders/<id>` | Signed in | same visibility rules as the HTML page |
| `POST /api/orders/<id>/cancel` | Customer | body `{}`; `409` once shipped |
| `POST /api/order-items/<id>/return` | Customer | `{reason}` (5 to 500 chars); `409` if not delivered or the window has closed |
| `POST /api/chat` | none | `{messages:[{role, content}]}`: 1 to 30 alternating turns that start and end with `user`, each ≤ 2000 chars; `429` over 20/min. Tools read orders only for the signed-in customer |

## Layout

`app.py` (factory, CLI) · `core.py` (auth, CSRF, validation, errors, stock rules) · `models.py` ·
`shop.py` (public, customer, messaging) · `seller.py` · `admin.py` · `api.py` · `shipping.py` (UPS) ·
`chatbot.py` · `seed.py` · `templates/` · `static/`

## Known simplifications

- Payment capture is simulated. The hook point is marked in `shop.place_order`.
- Tax is a single platform rate, not computed per destination.
- The rate limiter is in-process. Use Redis if you run more than one worker.
- Tables are created with `db.create_all()`. Add Alembic before the first schema change in production.
