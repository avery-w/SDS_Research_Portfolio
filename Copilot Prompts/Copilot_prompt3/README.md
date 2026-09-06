# MarketSquare

A production-oriented Flask marketplace for customers, sellers, and administrators. It includes product search, seller stores and inventory, cart and checkout, order fulfillment, image upload, role-scoped messaging, a rate-limited chatbot, admin analytics, and an UPS-style shipping estimator using `110 Inner Campus Drive, Austin, TX 78705` as the origin.

## Run locally

```powershell
cd "Copilot Prompts/Copilot_prompt3"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
$env:ADMIN_EMAIL="admin@example.com"
$env:ADMIN_PASSWORD="use-a-long-unique-password"
python app.py
```

Open `http://127.0.0.1:5000`. Set `COOKIE_SECURE=true` behind HTTPS. For production use PostgreSQL by setting `DATABASE_URL` to a psycopg connection string and serve with the included Gunicorn command or Docker Compose.

## Security notes

- Passwords are hashed with Werkzeug's PBKDF2 implementation; login and chatbot endpoints are rate limited.
- Mutating API requests require a session-bound CSRF token in `X-CSRF-Token`; cookies are HttpOnly and SameSite protected.
- Seller and customer routes enforce ownership server-side. Uploads use generated filenames, allowlisted extensions, and a 5 MB request limit.
- Production deployment must place the service behind TLS, rotate `SECRET_KEY`, use a managed secrets store, restrict database access, configure backups, scan dependencies, add an external rate-limit store, and use object storage plus malware/content scanning for uploads.
- The shipping endpoint is a transparent UPS-style dimensional-weight/zone estimate, not an official UPS quote. Integrate UPS OAuth/API credentials for live rates and labels.

## Main endpoints

`GET /api/products`, `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/cart`, `POST /api/checkout`, `POST /api/shipping/quote`, `GET /api/orders`, `POST /api/conversations`, `POST /api/conversations/<id>/messages`, `POST /api/chatbot`, and admin-only `GET /api/admin/analytics`.
