# Marketplace Full-Stack

This repository contains a Python FastAPI backend and a Vite+React frontend for a marketplace with three roles: `customer`, `seller`, and `admin`.

Features:
- Customers: browse/search products, manage cart, checkout, order history, return requests
- Sellers: manage stores/products, upload images, view and fulfill orders
- Admins: manage users/stores/products/orders and view sales analytics
- UPS-like shipping estimator from origin: 110 Inner Campus Drive, Austin, TX (configurable)
- AI chatbot endpoint (OpenAI optional) and messaging system

Quick dev setup (local, Python + Node installed):

1. Copy configuration:

```powershell
copy .env.example .env
# Edit .env to set SECRET_KEY and optionally OPENAI_API_KEY
```

2. Install backend dependencies and run the API:

```powershell
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

3. Install and start frontend:

```powershell
cd frontend
npm install
npm run dev
```

4. Open frontend: http://localhost:3000 and API docs: http://localhost:8000/docs

Docker Compose (Postgres + backend + frontend):

```powershell
# Builds and starts services
docker-compose up --build
```

Notes:
- The backend reads `DATABASE_URL` from `.env`. The provided `docker-compose.yml` configures a Postgres service and an example `DATABASE_URL` to connect to it.
- To enable AI chat, set `OPENAI_API_KEY` in `.env`.

If you'd like, I can:
- Add role-based UI flows and seller/product management pages in the frontend.
- Add tests, migrations (Alembic), and production config (NGINX, HTTPS).
