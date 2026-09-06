# Marketline Marketplace

A runnable Flask + SQLite marketplace starter for customers, sellers, and admins. It includes product discovery, carts, checkout, order service requests, seller fulfillment, image uploads, direct messaging, a deterministic customer chatbot, and admin analytics.

## Run locally

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SECRET_KEY = 'use-a-long-random-development-secret'
python app.py
```

Open <http://127.0.0.1:5000>.

The database is created and seeded on first start. Checkout estimates UPS Ground shipping from `110 Inner Campus Drive, Austin, TX 78705` using package weight and a destination zone. Demo accounts:

- Customer: `customer@example.com` / `password123`
- Seller: `seller@example.com` / `password123`
- Admin: `admin@example.com` / `password123`

For production, use a managed database, HTTPS, a real UPS API credential flow, a real payment processor, object storage, CSRF protection at the edge, rate limiting, secure session-cookie configuration, and a secrets manager. The included UPS calculation is a transparent estimate based on package weight and destination zone; it does not call UPS or represent a shipping quote.

## API surface

- `GET /api/products?q=&category=` browse/search products
- `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`
- `GET|POST|PATCH /api/cart` and `DELETE /api/cart/<product_id>`
- `POST /api/checkout` creates an order and calculates shipping
- `GET /api/orders`, `POST /api/orders/<id>/service-request`
- Seller: `GET|POST /api/seller/products`, `PATCH /api/seller/products/<id>`, `GET /api/seller/orders`, `PATCH /api/seller/orders/<id>`
- `GET|POST /api/messages`
- `POST /api/chatbot`
- Admin: `GET /api/admin/overview`, `PATCH /api/admin/users/<id>`

## Security and input audit

See `SECURITY_AUDIT.md` for every user-controlled value that reaches a query, file path, or shell boundary and the sanitization or safe API used. All SQL uses SQLite placeholders; no endpoint executes shell commands. Uploaded images are restricted by extension, MIME type, size, `secure_filename`, a generated server-side filename, and a fixed upload directory.
