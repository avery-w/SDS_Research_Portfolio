# Modern E-commerce Marketplace

Multi-role marketplace built with **FastAPI**, **SQLAlchemy**, **Jinja2**, and a lightweight frontend.

## Roles

| Role     | Capabilities |
|----------|--------------|
| **Customer** | Browse/search products, cart, checkout, order history, cancel/return requests, AI chat, message sellers |
| **Seller**   | Manage own store & products (with image upload), inventory, view/fulfill own orders |
| **Admin**    | Manage all users/stores/products/orders, deactivate accounts, override statuses, sales analytics |

## Features

- JWT authentication with role-based access control
- Product catalog with search
- Cart & checkout
- Shipping rate calculator using UPS-style dimensional weight + zone logic  
  **Origin fixed at:** 110 Inner Campus Drive, Austin, TX 78705
- AI chatbot (rule-based + optional OpenAI) that encourages messaging sellers in-app
- In-app messaging between customers and sellers
- Image upload for products
- Admin analytics dashboard

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env – at minimum set a strong SECRET_KEY

# 4. Run
python run.py
```

Open http://localhost:8000

API docs (Swagger): http://localhost:8000/docs

## Creating an Admin

Register a normal user, then promote it via SQLite / Python shell:

```python
from app.database import SessionLocal
from app.models import User, UserRole
db = SessionLocal()
u = db.query(User).filter_by(email="you@example.com").first()
u.role = UserRole.admin
db.commit()
```

Or use the `/admin/users/{id}/role` endpoint once you already have one admin.

## Shipping API

```http
POST /api/shipping/rates
{
  "dest_zip": "10001",
  "weight_lb": 2.5,
  "length_in": 12,
  "width_in": 9,
  "height_in": 4
}
```

Returns approximate UPS Ground rate from the fixed Austin origin.

## Project Layout

```
marketplace/
├── app/
│   ├── main.py          # FastAPI app entry
│   ├── config.py
│   ├── database.py
│   ├── models.py        # SQLAlchemy models (schema)
│   ├── schemas.py       # Pydantic schemas
│   ├── auth.py
│   ├── shipping.py      # UPS-style calculator
│   ├── chatbot.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── customer.py
│   │   ├── seller.py
│   │   ├── admin.py
│   │   └── api.py       # checkout, shipping, chat, messages
│   ├── templates/
│   └── static/
├── uploads/             # product images
├── requirements.txt
├── .env.example
├── run.py
└── README.md
```

## Production Notes

- Switch `DATABASE_URL` to PostgreSQL
- Replace the shipping module with the official UPS Rating API
- Add a real payment gateway (Stripe, etc.)
- Serve behind HTTPS + proper CORS
- Set a strong `SECRET_KEY` and never commit `.env`
- Consider background tasks for email notifications

## License

MIT – use freely.
