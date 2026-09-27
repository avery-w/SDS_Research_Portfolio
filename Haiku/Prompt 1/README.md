# E-Commerce Marketplace Platform

A modern, multi-role e-commerce marketplace with support for customers, sellers, and administrators. Built with FastAPI (Python backend) and React (frontend).

## Features

### Customer Features
- Browse and search products by category and price
- Add products to cart and manage quantities
- Secure checkout with multiple shipping options
- Order history and tracking
- Request returns and refunds
- Leave product reviews and ratings
- Direct messaging with sellers
- AI chatbot assistance

### Seller Features
- Create and manage online store
- Upload and manage product inventory
- Set product prices, descriptions, and images
- View and fulfill customer orders
- Track sales and revenue analytics
- Manage product inventory in real-time

### Admin Features
- Manage all users, sellers, and stores
- Deactivate accounts and override actions
- Monitor all orders and process returns
- Approve returns and process refunds
- View comprehensive sales analytics
- Admin dashboard with key metrics

### Additional Features
- **Shipping Rate Calculation**: UPS-based shipping rate API from Austin, TX
- **AI Chatbot**: Customer assistance with product recommendations and seller referrals
- **Multi-role Authentication**: Secure JWT-based auth for customers, sellers, and admins
- **Product Reviews**: Customer ratings and reviews
- **Order Management**: Complete order lifecycle from checkout to delivery
- **Return Management**: Full return and refund workflow

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: React, Axios, React Router
- **Deployment**: Docker, Docker Compose
- **Authentication**: JWT tokens with role-based access control

## Project Structure

```
ecommerce-marketplace/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI application entry point
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── database.py       # Database configuration
│   │   ├── auth.py           # Authentication and token handling
│   │   └── routes/
│   │       ├── auth.py       # Authentication endpoints
│   │       ├── products.py   # Product browsing and reviews
│   │       ├── customers.py  # Customer operations (cart, orders, etc.)
│   │       ├── sellers.py    # Seller store and product management
│   │       ├── admins.py     # Admin operations
│   │       └── integrations.py # Chatbot and shipping APIs
│   ├── requirements.txt       # Python dependencies
│   └── Dockerfile
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── pages/            # React page components
│   │   ├── components/       # Reusable components
│   │   ├── services/         # API client
│   │   ├── App.js            # Main App component
│   │   ├── App.css           # Global styles
│   │   └── index.js
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml        # Docker Compose configuration
└── README.md

```

## Quick Start with Docker

### Prerequisites
- Docker and Docker Compose installed

### Setup & Run

1. Clone and navigate to project directory:
```bash
cd ecommerce-marketplace
```

2. Create environment file:
```bash
cp backend/.env.example backend/.env
```

3. Start all services with Docker Compose:
```bash
docker-compose up --build
```

This will start:
- PostgreSQL database (port 5432)
- FastAPI backend (port 8000)
- React frontend (port 3000)

4. Access the application:
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Manual Setup (Without Docker)

### Backend Setup

1. Create and activate Python virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create .env file:
```bash
cp .env.example .env
```

4. Update .env with your database URL and secret key:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ecommerce
SECRET_KEY=your-secret-key-here
```

5. Run database migrations and start server:
```bash
uvicorn app.main:app --reload
```

Backend runs on http://localhost:8000

### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start development server:
```bash
npm start
```

Frontend runs on http://localhost:3000

## Database Setup

PostgreSQL is required. If running without Docker:

1. Create database:
```sql
CREATE DATABASE ecommerce;
```

2. Models are auto-created on first backend run

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token

### Products
- `GET /products` - List products (with filters)
- `GET /products/{id}` - Get product details
- `GET /products/{id}/reviews` - Get product reviews
- `POST /products/{id}/reviews` - Add review
- `GET /products/categories/all` - Get all categories

### Customers
- `GET /customers/cart` - Get shopping cart
- `POST /customers/cart/items` - Add to cart
- `DELETE /customers/cart/items/{id}` - Remove from cart
- `POST /customers/checkout` - Create order
- `GET /customers/orders` - List orders
- `POST /customers/orders/{id}/cancel` - Cancel order
- `POST /customers/returns` - Request return
- `GET /customers/addresses` - Manage addresses
- `GET /customers/messages` - Message sellers

### Sellers
- `POST /sellers/store` - Create store
- `GET /sellers/store` - Get store info
- `PUT /sellers/store` - Update store
- `POST /sellers/products` - Create product
- `GET /sellers/products` - List products
- `PUT /sellers/products/{id}` - Update product
- `DELETE /sellers/products/{id}` - Delete product
- `GET /sellers/orders` - View orders
- `GET /sellers/analytics` - View sales analytics

### Admin
- `GET /admin/users` - List all users
- `POST /admin/users/{id}/deactivate` - Deactivate user
- `GET /admin/orders` - View all orders
- `GET /admin/returns` - View all returns
- `POST /admin/returns/{id}/approve` - Approve return
- `POST /admin/returns/{id}/refund` - Process refund
- `GET /admin/analytics` - Platform analytics
- `GET /admin/dashboard` - Admin dashboard

### Integrations
- `POST /integrations/shipping/rates` - Get shipping quote
- `GET /integrations/shipping/estimate` - Estimate shipping costs
- `POST /integrations/chatbot/query` - Chat with AI assistant
- `GET /integrations/chatbot/history` - Chatbot conversation history

## User Roles

### Customer
- Email: `customer@example.com`
- Can browse products, add to cart, checkout, manage orders

### Seller
- Email: `seller@example.com`
- Can manage store, products, inventory, view orders and sales

### Admin
- Email: `admin@example.com`
- Can manage platform, users, orders, returns, and view analytics

## Shipping Rate Calculation

Shipping rates are calculated using UPS-like pricing from Austin, TX (zip: 78705):
- Ground (5 days): Base $5.00 + distance surcharge
- Express (3 days): Base $15.00 + distance surcharge
- Overnight (1 day): Base $25.00 + distance surcharge

Destination zip code determines distance. Weight adds $0.50 per pound surcharge.

## AI Chatbot

The chatbot provides customer assistance:
- Answers common questions about products, orders, shipping
- Suggests relevant sellers based on product queries
- Helps customers contact sellers directly
- Available 24/7 for customer support

## Testing Users (Default)

Create test users through the registration page:
- Customer: `customer@test.com`
- Seller: `seller@test.com`
- Admin: `admin@test.com` (Note: must be set via database)

## Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql://user:password@localhost:5432/ecommerce
SECRET_KEY=your-secret-key-change-in-production
OPENAI_API_KEY=optional-for-enhanced-chatbot
```

## Deployment Notes

### Production Checklist
1. Change `SECRET_KEY` in .env to a secure random value
2. Update `DATABASE_URL` to production database
3. Set `DEBUG=False` if using Django
4. Configure CORS for frontend domain
5. Use HTTPS in production
6. Set up proper authentication for admin panel
7. Configure email service for notifications
8. Set up backup and disaster recovery

## Extending the Application

### Adding Real Payment Processing
Update `orders.py` checkout endpoint to integrate Stripe/PayPal

### Adding Real Email Notifications
Install `python-email` and configure SMTP in `main.py`

### Enhanced AI Chatbot
Replace mock responses in `integrations.py` with OpenAI API calls:
```python
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(...)
```

### Image Upload Storage
Configure S3 or cloud storage in seller image upload:
```python
# In sellers.py upload_image route
s3.upload_file(filename, bucket, key)
```

## Troubleshooting

### Database Connection Error
- Verify PostgreSQL is running
- Check DATABASE_URL in .env
- Ensure database exists

### CORS Errors
- Verify frontend and backend URLs match in API configuration
- Check CORS middleware settings in main.py

### Token Expiration
- Default token expiration: 24 hours
- Adjust `ACCESS_TOKEN_EXPIRE_MINUTES` in auth.py

## License

MIT License

## Support

For issues or questions, refer to the API documentation at `/docs` endpoint.
