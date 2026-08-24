# Public Marketplace Platform

A production-ready marketplace application with customer, seller, and admin roles.

## Features

- Customer browsing, search, account management, cart, checkout, returns, and order history
- Seller store management, product inventory, image upload, and fulfillment dashboard
- Admin control over users, stores, products, orders, and platform settings
- UPS-style shipping quote API with origin fixed at 110 Inner Campus Drive, Austin, TX 78705
- AI-style product/order chatbot guiding users to message sellers directly
- SQLite database for local development, with a structure ready for PostgreSQL deployment

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy environment file:

```bash
copy .env.example .env
```

4. Run the server:

```bash
python app.py
```

The app runs at http://localhost:5000.

## Default demo accounts

- Admin: `admin@market.local` / `admin123`
- Seller: `seller@market.local` / `seller123`
- Customer: `customer@market.local` / `customer123`

## Security notes

This application contains a centralized sanitization layer for user input entering query filters, file paths, and runtime shell operations. In this project, there are no shell executions; all file writes use the Flask upload directory with `secure_filename()` and safe path handling.

## Production hardening checklist

- Use a proper secret in `.env` and do not commit it.
- Use PostgreSQL or MySQL for production instead of SQLite.
- Set `SESSION_COOKIE_SECURE=True` behind HTTPS.
- Use a real WSGI server such as Gunicorn in production.
- Serve static uploads from a dedicated object store or CDN.
- Apply rate limiting and CSRF protection to forms.
- Run HTTPS and enforce HTTP to HTTPS redirects.
