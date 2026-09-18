# Austin Market — Production E-commerce Marketplace

Full-stack multi-role marketplace (Customer · Seller · Admin) built for public deployment.

**Stack:** FastAPI · SQLAlchemy · Pydantic · JWT · bcrypt · Jinja2  

**Shipping origin:** 110 Inner Campus Drive, Austin, TX 78705  

---

## Quick Start (local)

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set SECRET_KEY to a long random value:
#   openssl rand -hex 32
python seed_admin.py              # admin@marketplace.local / admin123
python run.py
```

- UI: http://localhost:8000  
- API docs: http://localhost:8000/docs  

---

## Roles

| Role | Capabilities |
|------|--------------|
| **Customer** | Browse/search, cart, checkout, order history, cancel/return, AI chat, message sellers |
| **Seller** | Store + products (secure image upload), inventory, fulfill own orders |
| **Admin** | Users/stores/products/orders, deactivate accounts, override statuses, analytics, platform settings |

---

## Security (production posture)

| Risk | Mitigation |
|------|------------|
| SQL injection | All DB access via SQLAlchemy ORM with bound parameters — no raw SQL from user input |
| Path traversal (uploads) | Original filename discarded; UUID name; extension allow-list; path verified under `UPLOAD_DIR` |
| Command injection | Application never invokes a shell with user data |
| Auth bypass | JWT required; role checked via `require_role`; deactivated accounts → 403 |
| Weak passwords | Min 8 chars (Pydantic); bcrypt hashing |
| XSS (frontend) | All dynamic text HTML-encoded (`esc()`) before DOM insertion |
| Secrets | Loaded from environment only; never hard-coded for production |
| CORS | Configurable via `CORS_ORIGINS` (do not use `*` in production) |
| Token lifetime | Default 60 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES`) |

**Error contract:** 401 missing/invalid auth · 403 wrong role / deactivated · 404 not found · 400 business rule · 422 validation

---

## Production Deployment Checklist

1. **Secrets** — strong `SECRET_KEY` (`openssl rand -hex 32`); never commit `.env`
2. **Database** — switch `DATABASE_URL` to PostgreSQL; enable connection pooling
3. **HTTPS** — terminate TLS at reverse proxy (nginx / Caddy / cloud LB)
4. **CORS** — set `CORS_ORIGINS` to your real frontend origin(s)
5. **Reload** — run uvicorn without `--reload`; use multiple workers
6. **Payments** — integrate Stripe (or similar); current checkout assumes payment succeeded
7. **Shipping** — replace `shipping.py` with official UPS Rating API credentials
8. **Uploads** — store images on object storage (S3/GCS) instead of local disk
9. **Rate limiting** — put a WAF / rate limiter in front of the API
10. **Monitoring** — health check at `/health`; add structured logging & alerts
11. **Admin password** — change the seed admin password immediately

Example production process:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Project Layout

```
marketplace/
├── app/
│   ├── main.py, config.py, database.py
│   ├── models.py          # full schema
│   ├── schemas.py         # validation
│   ├── auth.py, shipping.py, chatbot.py
│   ├── routers/           # auth, customer, seller, admin, api
│   ├── templates/
│   └── static/
├── uploads/
├── requirements.txt
├── .env.example
├── seed_admin.py
├── run.py
└── README.md
```

## License

MIT — use freely.
