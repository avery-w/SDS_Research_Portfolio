# Kilo Marketplace

A full-stack, production-ready e-commerce marketplace built with
**FastAPI**, **SQLAlchemy**, **HTMX**, and **Tailwind CSS**.

## Features

| Area | Highlights |
|------|------------|
| **Three roles** | Customer, Seller, Admin — each with dedicated dashboards |
| **Catalog** | Product search, filtering, categories, rich product pages |
| **Cart & Checkout** | Persistent cart, address management, order summary |
| **Shipping** | UPS guideline-based rate calculation from 110 Inner Campus Dr, Austin, TX |
| **Orders** | Full status lifecycle, order history, cancellations, returns |
| **Messaging** | AI chatbot + direct customer↔seller messaging |
| **Seller tools** | Store management, product/inventory, order fulfillment, analytics |
| **Admin panel** | User/store/product/order management, analytics, platform settings |
| **Security** | JWT auth, RBAC, audit logging, input validation, secure cookies |

## Quick start

```bash
cd kilo_auto_1
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn main:app --reload
```

Then open <http://localhost:8000>.

API docs: <http://localhost:8000/docs>

## Testing

```bash
pytest
```

## Tech stack

- **FastAPI** – async web framework & REST API
- **SQLAlchemy 2** – ORM with SQLite file DB (PostgreSQL-ready)
- **Jinja2 + HTMX + Alpine.js + Tailwind** – server-rendered modern UI
- **JWT** – access & refresh token authentication
- **Celery + Redis** – background email tasks (stub)
