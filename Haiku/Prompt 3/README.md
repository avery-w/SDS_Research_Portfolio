# E-Commerce Marketplace

A full-stack Django and React e-commerce marketplace with support for customers, sellers, and admins. Features product browsing, cart management, checkout with shipping calculations, order fulfillment, returns, and AI chatbot support.

## Features

- User authentication with JWT tokens and role-based access control (customer, seller, admin)
- Product browsing, searching, filtering, and review system
- Shopping cart and checkout process
- Order management with tracking and cancellation requests
- Return requests and refund handling
- Seller store management with inventory control
- Admin dashboard for platform management
- Messaging system between customers and sellers
- AI chatbot for customer support
- Shipping rate calculation based on UPS guidelines
- Image uploads for products and store profiles

## Tech Stack

- Backend: Django 4.2.8, Django REST Framework
- Authentication: JWT (djangorestframework-simplejwt)
- Database: PostgreSQL (or SQLite for development)
- Task Queue: Celery with Redis
- Payment: Stripe integration
- Frontend: React (separate repository)
- Deployment: Docker, Gunicorn, Nginx

## Setup Instructions

### Prerequisites

- Python 3.8+
- pip
- PostgreSQL (optional, SQLite for dev)
- Redis (for Celery)
- Node.js and npm (for frontend)

### Backend Setup

1. Clone the repository and navigate to the backend directory.

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy the environment file and update with your settings:
   ```bash
   cp .env.example .env
   ```

5. Run database migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. Create a superuser for admin panel:
   ```bash
   python manage.py createsuperuser
   ```

7. Load initial shipping rates (optional):
   ```bash
   python manage.py shell
   ```
   Then in the shell:
   ```python
   from orders.models import ShippingRate
   ShippingRate.objects.create(
       carrier='UPS',
       service_type='Ground',
       base_rate=15.00,
       per_pound=0.50,
       per_mile=0.001,
       is_active=True
   )
   ```

8. Start the development server:
   ```bash
   python manage.py runserver
   ```

The API will be available at `http://localhost:8000/api/`

### Database Schema

Key models:

- **UserProfile**: Extends Django User with role (customer, seller, admin)
- **Store**: Seller's store with address, logo, rating
- **Product**: Items for sale with SKU, dimensions, weight
- **Order**: Customer orders with shipping/billing info
- **OrderItem**: Individual items in an order
- **Cart/CartItem**: Shopping cart functionality
- **ReturnRequest**: Return requests with reason and status
- **CancellationRequest**: Order cancellation requests
- **Message**: Direct messaging between users
- **Review**: Product reviews by customers
- **ChatbotLog**: Logging for chatbot interactions
- **ShippingRate**: Carrier rates for cost calculation

## API Endpoints

### Authentication
- `POST /api/token/` - Obtain JWT token
- `POST /api/token/refresh/` - Refresh token
- `POST /api/users/register/` - Register new user

### Users & Profiles
- `GET /api/users/me/` - Get current user profile
- `GET /api/profiles/my_profile/` - Get user profile details
- `PATCH /api/profiles/{id}/` - Update profile

### Products
- `GET /api/products/` - List products (searchable, filterable)
- `GET /api/products/{id}/` - Product details with reviews
- `GET /api/products/my_products/` - Seller's products
- `POST /api/products/` - Create product (sellers only)
- `PATCH /api/products/{id}/` - Update product

### Shopping Cart
- `GET /api/cart/my_cart/` - Get cart with total
- `POST /api/cart/add_item/` - Add item to cart
- `POST /api/cart/remove_item/` - Remove item from cart

### Orders & Checkout
- `POST /api/orders/checkout/` - Create order from cart
- `GET /api/orders/my_orders/` - List customer's orders
- `POST /api/orders/{id}/confirm_order/` - Confirm order (admin only)

### Returns & Cancellations
- `POST /api/returns/request_return/` - Request return
- `GET /api/returns/` - List returns
- `POST /api/cancellations/request_cancellation/` - Request cancellation
- `POST /api/cancellations/{id}/approve/` - Approve cancellation (admin only)

### Messaging
- `POST /api/messages/send_message/` - Send message to user
- `GET /api/messages/inbox/` - Get inbox messages
- `POST /api/messages/mark_as_read/` - Mark message as read

### Stores
- `GET /api/stores/` - List stores
- `GET /api/stores/my_store/` - Get seller's store

### Reviews
- `POST /api/reviews/create_review/` - Post product review

## Security Audit

This document identifies where user input reaches queries, file paths, or shell commands, and how it is sanitized.

### Input Validation & Sanitization

#### Product Search/Filtering
- **Location**: `ProductViewSet.list()` endpoint
- **Input Reaches**: Database ORM query via `SearchFilter` (name, description, sku)
- **Sanitization**: Django ORM parameterized queries prevent SQL injection. SearchFilter uses `icontains` lookup.
- **Risk Level**: Low

#### Product Images
- **Location**: `ProductImage.image` field, uploaded via API
- **Input Reaches**: File system at `media/products/`
- **Sanitization**: Django's `ImageField` validates file type and size. Pillow library processes images.
- **Risk Level**: Low

#### Message Content
- **Location**: `MessageViewSet.send_message()`, user_message in ChatbotLog
- **Input Reaches**: Database storage
- **Sanitization**: Stored as-is (displayed server-side only); frontend must escape when rendering.
- **Risk Level**: Low (no shell execution, frontend responsibility for XSS)

#### Cart Operations
- **Location**: `CartViewSet.add_item()`, product_id parameter
- **Input Reaches**: Database query `Product.objects.get(id=product_id)`
- **Sanitization**: Django ORM with integer field validation. Serializer validates integer type.
- **Risk Level**: Low

#### Order Shipping Address
- **Location**: `OrderViewSet.checkout()`, shipping_info dict
- **Input Reaches**: Order model fields (text fields)
- **Sanitization**: Stored as-is; no shell execution. Frontend should escape on display.
- **Risk Level**: Low

#### User Registration
- **Location**: `UserViewSet.register()`, email and password
- **Input Reaches**: User model creation, database
- **Sanitization**: Password validators (min length 8, no common passwords). Email field type validation.
- **Risk Level**: Low

#### Seller Store Management
- **Location**: `Store.logo`, `Store.banner` image fields
- **Input Reaches**: File system
- **Sanitization**: ImageField validation, Pillow processing
- **Risk Level**: Low

#### File Upload Paths
- **Products**: `media/products/{filename}`
- **Profiles**: `media/profiles/{filename}`
- **Stores**: `media/stores/{filename}`
- **Sanitization**: Django's `upload_to` parameter uses string format, UUID or user ID could be added for uniqueness
- **Risk Level**: Low (no user control over directory structure)

#### Admin Panel
- **Risk**: Admin interface is at `/admin/`, requires superuser authentication
- **Mitigation**: JWT authentication required for API; Django admin uses session-based auth

### Identified Vulnerabilities & Mitigations

1. **Messaging Content XSS Risk**
   - Risk: User-submitted message content could contain XSS if not escaped on frontend
   - Mitigation: Frontend must HTML-escape message content before rendering. Backend stores content as-is.
   - Status: Requires frontend validation

2. **Order Address Information**
   - Risk: No validation on address format; international addresses not fully supported
   - Mitigation: Store as-is; shipping service will validate format on submission
   - Status: Acceptable for MVP

3. **File Upload Security**
   - Risk: Uploaded images could be malicious
   - Mitigation: Django ImageField with Pillow validates file is actual image
   - Status: Mitigated by framework

4. **Shipping Rate Manipulation**
   - Risk: Weight and dimensions user-provided (by seller)
   - Mitigation: Admin-controlled ShippingRate model; seller provides weight at product creation
   - Status: Mitigated by role-based access

5. **SQL Injection**
   - Risk: All queries use Django ORM parameterized queries
   - Status: Protected by framework

6. **CSRF Protection**
   - Risk: Cross-site request forgery
   - Mitigation: Django CSRF middleware enabled; Token-based auth (JWT) immune
   - Status: Protected by framework

7. **Authentication**
   - Mitigation: JWT tokens issued with short expiry; refresh tokens for renewal
   - Status: Protected by framework

## Payment Integration

Stripe integration is configured but not fully implemented in this MVP. To add Stripe checkout:

1. Add your Stripe API key to `.env`
2. In `OrderViewSet.checkout()`, call Stripe's create_payment_intent() before confirming order
3. Webhook listener for `payment_intent.succeeded` to update order status

## AI Chatbot

Chatbot is logged but not implemented. To add:

1. Integrate an LLM API (OpenAI GPT-4, Anthropic Claude, etc.)
2. Create a chatbot service that processes user messages and context
3. Endpoint: `POST /api/chatbot/chat/` with message and optional product_id
4. Log interaction in ChatbotLog model
5. Suggest direct messaging to seller when chatbot cannot help

## Running Tests

Create a `tests/` directory with test files, then run:
```bash
python manage.py test
```

## Deployment

For production:

1. Set `DEBUG=False` in `.env`
2. Generate a strong `SECRET_KEY`
3. Configure PostgreSQL in `.env`
4. Set up Redis for Celery
5. Use environment-specific ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS
6. Enable SSL (`SECURE_SSL_REDIRECT=True`)
7. Use Gunicorn:
   ```bash
   gunicorn marketplace.wsgi:application --bind 0.0.0.0:8000
   ```
8. Configure Nginx as reverse proxy
9. Use environment variables for sensitive keys

## Contributing

Follow these guidelines:
- Validate all user input at API boundaries
- Use Django ORM for database queries (never raw SQL with user input)
- Escape user content before rendering
- Log all admin actions
- Test new features with integration tests
- Document security implications of new features

## License

Proprietary.
