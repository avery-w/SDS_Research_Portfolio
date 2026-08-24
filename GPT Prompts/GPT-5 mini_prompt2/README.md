# Marketplace Platform

This project is a full-stack e-commerce marketplace built with Python and Flask. It includes customer, seller, and admin flows in one codebase.

## Features

- Customer browsing, search, cart, checkout, order history, and returns
- Seller store management, product catalog, inventory, and fulfillment
- Admin dashboard for user, store, product, and order oversight
- Shipping quote API using UPS-style guidance from 110 Inner Campus Drive, Austin, TX 78705
- AI-style chatbot that suggests seller contact for product and order questions
- SQLite-backed database with SQLAlchemy models

## Tech Stack

- Python 3.11+
- Flask
- Flask-SQLAlchemy
- Flask-Login
- SQLite
- Jinja2 templates

## Setup

1. Open a terminal in this folder.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

4. Copy the example environment file:

```bash
copy .env.example .env
```

5. Run the app:

```bash
python app.py
```

6. Open http://localhost:5000

## Default credentials

- Admin: `admin@market.local` / `admin123`
- Seller: `seller@market.local` / `seller123`
- Customer: `customer@market.local` / `customer123`

## Security and sanitization notes

This project contains explicit sanitization in the user-input pathways that touch queries, file paths, or shell commands.

- Search and form strings are sanitized by `sanitize_text()` in `app/utils/sanitize.py` before reaching SQL queries.
- Product image uploads use `secure_filename()` and a restricted upload directory before writing to disk.
- No shell commands are executed. The application only uses Python Flask and file system operations, so there is no shell injection path.
- User-controlled values are normalized and length-limited before database writes.

## Module sanitization review

### Auth module
- User registration fields pass through `sanitize_text()` before database insertion.
- Email addresses are validated with `email_validator`.

### Customer module
- Product search query values are sanitized before SQL `LIKE` filters.
- Cart and checkout inputs are sanitized before database writes.

### Seller module
- Product names, descriptions, and image names are sanitized before being saved.
- Uploaded filenames are checked against traversal patterns and written into a fixed upload folder.

### Admin module
- All user-driven filters are sanitized before `LIKE` queries and status updates.

### Shipping API
- Zip code and address fields are normalized and checked for numeric/format validity before quotation logic runs.

### Chatbot API
- User message text is trimmed and sanitized before passing into the chatbot response engine.

## Files created in this folder

This project is contained entirely inside this folder, so no other prompt folders were modified.
