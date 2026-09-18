# Austin Market — Full-Stack E-commerce Marketplace

Modern multi-role marketplace built with **FastAPI**, **SQLAlchemy**, **Jinja2**, and a polished dark UI.

## Roles

| Role | Capabilities |
|------|--------------|
| **Customer** | Browse/search products, cart, checkout, order history, cancel/return requests, AI chat, message sellers |
| **Seller** | Own store & products (image upload), inventory, view/fulfill orders |
| **Admin** | Manage users/stores/products/orders, deactivate accounts, override statuses, sales analytics, platform settings |

## Key Features

- JWT auth with strict role checks on every protected endpoint
- Explicit handling of **401** (missing/invalid auth), **403** (wrong role / deactivated), **404**, **400**, **422**
- Checkout API that calculates shipping using UPS-style dimensional weight + zone logic  
  **Origin fixed at 110 Inner Campus Drive, Austin, TX 78705**
- AI chatbot (rule-based + optional OpenAI) that always steers customers to message sellers in-app
- In-app messaging
- Admin analytics dashboard + platform settings key-value store
- Image upload with type/size validation
- Production-oriented structure, validation, and error messages

## Quick Start

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # set a strong SECRET_KEY
python seed_admin.py              # admin@marketplace.local / admin123
python run.py
```

- UI → http://localhost:8000  
- API docs → http://localhost:8000/docs  

## Error Contract (every endpoint)

| Situation | Status |
|-----------|--------|
| Missing / invalid / expired JWT | **401** |
| Authenticated but wrong role or deactivated account | **403** |
| Resource not found or not owned | **404** |
| Business rule violation (empty cart, bad status transition, etc.) | **400** |
| Pydantic / form validation failure | **422** |

## Project Layout

```
marketplace/
├── app/
│   ├── main.py, config.py, database.py
│   ├── models.py          # full schema
│   ├── schemas.py         # Pydantic models with validators
│   ├── auth.py, shipping.py, chatbot.py
│   ├── routers/           # auth, customer, seller, admin, api
│   ├── templates/         # modern SPA-style UI
│   └── static/            # CSS + JS
├── uploads/
├── requirements.txt
├── .env.example
├── seed_admin.py
├── run.py
└── README.md
```

## Production Notes

- Point `DATABASE_URL` at PostgreSQL
- Replace `shipping.py` with the official UPS Rating API
- Add a real payment provider (Stripe, etc.)
- Serve behind HTTPS, tighten CORS, rotate `SECRET_KEY`
- Never commit `.env`

MIT License — use freely.
