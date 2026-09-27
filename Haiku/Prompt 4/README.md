# E-Commerce Marketplace

A production-ready full-stack Python e-commerce marketplace with three user roles (customer, seller, admin), complete payment processing, shipping calculations, and AI chatbot support.

## Features

### Customer Features
- Browse and search products
- Add items to cart and manage quantities
- Checkout with shipping address and payment
- Track order status
- Request returns for delivered orders
- Submit product reviews
- AI-powered customer support chatbot
- Message sellers about orders

### Seller Features
- Create and manage multiple stores
- Add and update products with inventory
- Track and manage orders from customers
- Mark orders as shipped with tracking numbers
- Approve return requests
- View sales analytics

### Admin Features
- Manage all users and sellers
- Deactivate/activate user accounts
- Change user roles
- Monitor platform analytics
- View sales, user, and product statistics
- Manage all stores and products

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Authentication**: JWT with bcrypt password hashing
- **Payment**: Stripe API integration
- **Shipping**: UPS API integration (with fallback calculations)
- **AI**: OpenAI API integration
- **Server**: Uvicorn

### Frontend
- **Framework**: React 18
- **Routing**: React Router v6
- **HTTP Client**: Axios
- **Styling**: CSS with responsive grid layout

### Deployment
- **Containerization**: Docker
- **Orchestration**: Docker Compose

## Prerequisites

- Docker and Docker Compose
- Or locally: Python 3.11+, Node.js 18+, PostgreSQL 15+

## Quick Start with Docker

1. Clone the repository:
```bash
git clone <repo-url>
cd ecommerce-marketplace
```

2. Create environment file:
```bash
cp .env.example .env
```

3. Start all services:
```bash
docker-compose up --build
```

4. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Local Development Setup

### Backend Setup

1. Create Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up PostgreSQL:
```bash
createdb ecommerce
createuser ecommerce
# Set password: ecommerce
```

4. Run migrations (database tables are created automatically):
```bash
python -m app.main
```

5. Start the server:
```bash
uvicorn app.main:app --reload
```

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create .env file:
```bash
echo "REACT_APP_API_URL=http://localhost:8000" > .env
```

4. Start development server:
```bash
npm start
```

## Database Schema

### Core Tables
- **users**: User accounts with roles (customer, seller, admin)
- **addresses**: Shipping and billing addresses
- **stores**: Seller stores
- **products**: Product listings with inventory
- **product_images**: Product images
- **orders**: Customer orders
- **order_items**: Items in each order
- **cart_items**: Shopping cart items
- **reviews**: Product reviews
- **messages**: Chat messages between customers and chatbot/sellers

## API Documentation

Full API documentation is available at `/docs` (Swagger UI) or `/redoc` (ReDoc).

### Key Endpoints

**Authentication**
- `POST /auth/register` - Register new user
- `POST /auth/token` - Login
- `GET /auth/me` - Get current user

**Products**
- `GET /products` - List products with search
- `GET /products/{id}` - Get product details
- `POST /products/{id}/reviews` - Add product review
- `GET /products/{id}/reviews` - Get product reviews

**Cart**
- `GET /cart` - View cart
- `POST /cart` - Add item to cart
- `PUT /cart/{item_id}` - Update item quantity
- `DELETE /cart/{item_id}` - Remove item
- `DELETE /cart` - Clear cart

**Orders**
- `GET /orders` - List user's orders
- `GET /orders/{id}` - Get order details
- `POST /orders/{id}/cancel` - Cancel order
- `POST /orders/{id}/request-return` - Request return

**Checkout**
- `POST /checkout/shipping-rate` - Calculate shipping cost
- `POST /checkout/create-order` - Create order from cart
- `POST /checkout/process-payment` - Process payment

**Seller**
- `POST /stores` - Create store
- `POST /stores/{id}/products` - Add product to store
- `PUT /stores/{id}/products/{product_id}` - Update product

**Admin**
- `GET /admin/users` - List all users
- `PUT /admin/users/{id}/role` - Change user role
- `POST /admin/users/{id}/deactivate` - Deactivate user
- `GET /admin/analytics/sales` - Sales analytics
- `GET /admin/analytics/users` - User analytics
- `GET /admin/analytics/products` - Product analytics

## Configuration

### Environment Variables

Create a `.env` file with:

```
DATABASE_URL=postgresql://ecommerce:ecommerce@localhost:5432/ecommerce
SECRET_KEY=your-secret-key-change-in-production
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_key
OPENAI_API_KEY=sk-your-openai-key
```

## Security Features

- ✅ Password hashing with bcrypt
- ✅ JWT authentication with expiration
- ✅ Role-based access control (RBAC)
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ CORS configuration
- ✅ Input validation with Pydantic
- ✅ Secure password reset flow ready
- ✅ Rate limiting ready (add with middleware)

## Testing

### Test User Accounts

1. Register at `/register` with any email
2. Create a seller account and promote via admin
3. Create an admin account (requires database update)

### Test Data

Sample products can be added via the Seller Dashboard after creating a store.

## Deployment

### Production Checklist

1. Generate strong `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

2. Update `.env` with production credentials:
   - Real Stripe API keys
   - Real OpenAI API key
   - Real PostgreSQL connection string
   - Strong SECRET_KEY

3. Set `DEBUG=False` in production

4. Use production-grade PostgreSQL instance

5. Deploy with Docker:
```bash
docker-compose -f docker-compose.yml up -d
```

### Environment-Specific Configuration

The app detects test mode keys:
- Stripe test keys: responses are mocked
- OpenAI placeholder key: uses rule-based chatbot
- UPS mocked: realistic rates calculated without API

## Shipping Rate Calculation

Shipping rates are calculated based on:
- Package weight (ounces converted to pounds)
- Distance from warehouse (Austin, TX 78705)
- Base rate: $5.99 + weight charges + distance multiplier

Example:
- 1 lb package, local: $5.99
- 5 lb package, regional: $8.49 + (15% distance multiplier)
- 20+ lb package, cross-country: $13.99 + (50% distance multiplier)

## AI Chatbot

The chatbot uses OpenAI's API in production. In test mode, it provides rule-based responses for:
- Order tracking
- Returns and refunds
- Shipping information
- Seller contact
- Password reset help

## Support

For issues or questions:
1. Check API documentation at `/docs`
2. Review database schema in `app/models.py`
3. Check error messages in logs
4. Review sample requests in frontend pages

## License

MIT License - See LICENSE file for details

## Notes

- All external API integrations (Stripe, OpenAI, UPS) support test mode
- Database is automatically initialized on first run
- CORS is configured for localhost development
- Frontend runs on port 3000, backend on port 8000
- All passwords are securely hashed
- JWT tokens expire after 30 minutes by default
