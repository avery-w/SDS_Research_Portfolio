# LongCat Marketplace

A modern, full-featured e-commerce marketplace built with Python and Flask. Supports three user roles: customers, sellers, and administrators.

## Features

### Customers
- Browse and search products with filtering and sorting
- Shopping cart management
- Secure checkout with shipping rate calculation
- Order history and tracking
- Cancel orders and request returns
- Direct messaging with sellers
- AI-powered shopping assistant

### Sellers
- Store management (logo, banner, description)
- Product management with image uploads
- Inventory tracking
- Order fulfillment and status updates
- Sales analytics dashboard
- Direct messaging with customers
- Return request handling

### Administrators
- Full platform dashboard with analytics
- User management (activate/deactivate, role changes)
- Store approval and management
- Product management across all stores
- Order management with override capabilities
- Category management
- Platform settings configuration
- Sales analytics with charts

### Additional Features
- **UPS Shipping Rate API**: Calculates real-time shipping rates based on UPS guidelines, with origin at 110 Inner Campus Drive, Austin, TX 78705
- **AI Chatbot**: Assists customers and encourages direct seller communication
- **RESTful API**: Full JSON API for cart, checkout, orders, and messaging

## Tech Stack

- **Backend**: Python 3.10+, Flask 3.0
- **Database**: SQLite (development) / PostgreSQL (production)
- **ORM**: SQLAlchemy 2.0
- **Auth**: Flask-Login with Werkzeug password hashing
- **Forms**: Flask-WTF with CSRF protection
- **Frontend**: Bootstrap 5, Jinja2 templates
- **Charts**: Chart.js
- **AI**: OpenAI API integration
- **Shipping**: UPS Rates API (with mock fallback)

## Quick Start

### 1. Clone and Setup

```bash
cd LongCat2_0
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Initialize Database

```bash
flask init-db
```

This creates sample data:
- Admin: admin@longcat.com / admin123
- Seller: seller@longcat.com / seller123
- Customer: customer@longcat.com / customer123

### 4. Run

```bash
python run.py
```

Visit http://localhost:5000

## Project Structure

```
LongCat2_0/
├── app/
│   ├── __init__.py          # App factory
│   ├── models.py            # Database models
│   ├── forms.py             # WTForms
│   ├── routes/
│   │   ├── auth.py          # Auth + public pages
│   │   ├── customer.py      # Customer routes
│   │   ├── seller.py        # Seller routes
│   │   ├── admin.py         # Admin routes
│   │   ├── api.py           # REST API
│   │   └── chatbot.py       # AI chatbot
│   ├── services/
│   │   ├── shipping.py      # UPS shipping rates
│   │   └── chatbot.py       # AI chatbot service
│   ├── utils/
│   │   ├── decorators.py    # Role-based access
│   │   ├── helpers.py       # Utility functions
│   │   └── template_filters.py
│   ├── templates/           # Jinja2 templates
│   └── static/              # CSS, JS, uploads
├── config.py                # Configuration
├── run.py                   # Entry point
├── requirements.txt         # Dependencies
└── .env.example             # Environment template
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/products | List products |
| GET | /api/product/:slug | Product detail |
| GET | /api/cart | Get cart |
| POST | /api/cart/add | Add to cart |
| PUT | /api/cart/update/:id | Update quantity |
| DELETE | /api/cart/remove/:id | Remove item |
| POST | /api/checkout/calculate-shipping | Get shipping rates |
| POST | /api/checkout | Place order |
| GET | /api/orders | List orders |
| GET | /api/order/:number | Order detail |
| GET | /api/categories | List categories |
| POST | /api/messages/send | Send message |
| GET | /api/admin/stats | Platform stats |

## Database Schema

- **Users**: Authentication, profiles, roles
- **Stores**: Seller storefronts
- **Categories**: Product categorization
- **Products**: Items for sale with inventory
- **CartItems**: Shopping cart entries
- **Orders/OrderItems**: Purchase records
- **Messages**: User-to-user communication
- **ReturnRequests**: Return/refund requests
- **PlatformSettings**: Configurable platform values
- **Reviews**: Product reviews

## Shipping Integration

The shipping service uses UPS guidelines with the origin address:
**110 Inner Campus Drive, Austin, TX 78705**

When `UPS_USE_MOCK=true` (default), rates are calculated locally using UPS pricing formulas. Set `UPS_API_KEY` and `UPS_USE_MOCK=false` to use the live UPS API.

## AI Chatbot

The chatbot uses OpenAI's API when `OPENAI_API_KEY` is set. Without an API key, it falls back to rule-based responses covering:
- Product inquiries (with seller connection)
- Shipping information
- Return policy
- Payment methods
- Order tracking

## Production Deployment

```bash
export FLASK_ENV=production
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export DATABASE_URL=postgresql://user:pass@host/dbname
gunicorn -w 4 -b 0.0.0.0:8000 "run:app"
```

## License

MIT License
