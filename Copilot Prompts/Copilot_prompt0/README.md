Django E-commerce marketplace (minimal scaffold)

Quick start (SQLite, local development):

1. Create a virtualenv and activate it:
   python -m venv .venv
   .\.venv\Scripts\activate

2. Install dependencies:
   pip install -r requirements.txt

3. Run migrations and create a superuser:
   python manage.py migrate
   python manage.py createsuperuser

4. Run the dev server:
   python manage.py runserver

Key API endpoints:
- /api/products/          (GET, POST for products)
- /api/orders/checkout/   (POST) - returns mocked UPS-based shipping rate
- /api/chat/message/      (POST) - rule-based chatbot and optional message routing to seller

Notes:
- Uses SQLite by default (db.sqlite3 in project root).
- Image uploads require Pillow and configuring MEDIA settings in production.
- Checkout shipping calculation is mocked; replace with real UPS API integration if desired.
