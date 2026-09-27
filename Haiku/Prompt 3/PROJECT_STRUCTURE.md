# Project Structure

Complete e-commerce marketplace with Django REST API backend and React frontend.

## Directory Structure

```
marketplace/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── .gitignore               # Git ignore rules
├── README.md                # Main documentation
├── QUICKSTART.md            # Quick start guide
├── DEPLOYMENT.md            # Production deployment guide
├── SECURITY.md              # Security audit & guidelines
├── PROJECT_STRUCTURE.md     # This file
│
├── marketplace/             # Django project settings
│   ├── __init__.py
│   ├── settings.py          # Django configuration
│   ├── urls.py              # URL routing
│   └── wsgi.py              # WSGI application
│
├── core/                    # Core app (users, products, messaging)
│   ├── __init__.py
│   ├── admin.py             # Django admin configuration
│   ├── apps.py              # App configuration
│   ├── models.py            # User, Store, Product models
│   ├── views.py             # API views
│   ├── serializers.py       # DRF serializers
│   ├── chatbot.py           # AI chatbot logic
│   └── tests.py             # Test cases
│
├── orders/                  # Orders app
│   ├── __init__.py
│   ├── admin.py             # Django admin
│   ├── apps.py              # App configuration
│   ├── models.py            # Order models
│   ├── views.py             # Order API views
│   ├── serializers.py       # Order serializers
│   └── shipping.py          # Shipping rate calculator
│
└── frontend/                # React frontend
    ├── package.json         # Node dependencies
    ├── public/
    │   └── index.html       # HTML entry point
    └── src/
        ├── index.js         # React entry
        ├── index.css        # Global styles
        ├── App.js           # Main app component
        ├── App.css          # App styles
        ├── api.js           # API client
        ├── components/
        │   ├── Header.js    # Navigation header
        │   └── Header.css
        ├── pages/
        │   ├── Home.js              # Product browse
        │   ├── Login.js             # User login
        │   ├── Register.js          # User registration
        │   ├── ProductDetail.js     # Product detail & reviews
        │   ├── Cart.js              # Shopping cart
        │   ├── Checkout.js          # Checkout form
        │   ├── OrderHistory.js      # Order history
        │   ├── Messages.js          # Messaging interface
        │   ├── Profile.js           # User profile
        │   ├── SellerDashboard.js   # Seller store management
        │   └── AdminDashboard.js    # Admin analytics
        └── styles/
            ├── Home.css             # Home page styles
            ├── Auth.css             # Login/Register styles
            └── Common.css           # Shared component styles
```

## Backend Files Summary

### Django Configuration
- `settings.py`: Database, installed apps, middleware, authentication, CORS
- `urls.py`: API routing with DRF routers
- `wsgi.py`: WSGI application entry point

### Core App (core/)
- `models.py`: 
  - UserProfile (role-based: customer, seller, admin)
  - Store (seller store information)
  - Product (items for sale)
  - ProductImage (product images)
  - Review (customer reviews)
  - Cart & CartItem (shopping cart)
  - Message (user messaging)
  - ChatbotLog (chatbot interaction history)

- `views.py`: ViewSets for:
  - Users (registration, profile, authentication)
  - Products (browse, search, filter)
  - Cart (add/remove items)
  - Messages (inbox, send)
  - Chatbot (rule-based responses)

- `serializers.py`: DRF serializers for all models
- `chatbot.py`: Rule-based chatbot logic
- `admin.py`: Django admin registration

### Orders App (orders/)
- `models.py`:
  - Order (customer orders)
  - OrderItem (items in order)
  - ReturnRequest (return management)
  - CancellationRequest (order cancellation)
  - ShippingRate (carrier rates)

- `views.py`: ViewSets for:
  - Orders (checkout, history)
  - Returns (request return)
  - Cancellations (request cancellation)

- `shipping.py`: UPS zone-based shipping calculator
- `serializers.py`: Order serializers

## Frontend Files Summary

### React Components
- `App.js`: Main router and authentication state
- `Header.js`: Navigation bar
- `api.js`: API client with JWT interceptors

### Pages
- `Home.js`: Product listing with search
- `Login.js` / `Register.js`: Authentication
- `ProductDetail.js`: Product info, reviews, chatbot
- `Cart.js`: Shopping cart management
- `Checkout.js`: Order creation
- `OrderHistory.js`: View past orders
- `Messages.js`: User messaging interface
- `Profile.js`: User profile management
- `SellerDashboard.js`: Seller store & product management
- `AdminDashboard.js`: Analytics and user management

### Styles
- `Home.css`: Product grid and search styling
- `Auth.css`: Login/register form styling
- `Common.css`: Shared component styles (cart, orders, messages)

## Database Schema

### Users & Profiles
```
User (Django built-in)
  └── UserProfile (role, contact info, profile image)
```

### Stores & Products
```
Store (seller store)
  └── Product (items for sale)
      ├── ProductImage (product images)
      └── Review (customer reviews)
```

### Shopping
```
Cart
  └── CartItem
      └── Product
```

### Orders
```
Order (customer order)
  └── OrderItem (items in order)
  ├── ReturnRequest (return requests)
  └── CancellationRequest (cancellation requests)
```

### Shipping
```
ShippingRate (carrier rates)
```

### Communication
```
Message (user to user)
ChatbotLog (chatbot interactions)
```

## Key Features Implemented

### ✅ Customer Features
- User registration and login
- Browse and search products
- Product details with reviews
- Shopping cart management
- Checkout with shipping address
- Order history and tracking
- Return and cancellation requests
- Message sellers directly
- AI chatbot assistance

### ✅ Seller Features
- Seller registration
- Store management
- Product creation with images and specifications
- Inventory management
- Order fulfillment view
- Analytics on sales

### ✅ Admin Features
- User management (deactivate accounts)
- Platform analytics (users, orders, revenue)
- Order management
- Return/cancellation approval
- Shipping rate management
- System settings

### ✅ API Features
- JWT token authentication
- Role-based access control
- Pagination and filtering
- Search functionality
- Product recommendations (via reviews)
- Shipping rate calculation based on UPS zones

### ✅ Security Features
- Password hashing (PBKDF2)
- JWT authentication with refresh tokens
- CORS protection
- CSRF protection
- ORM parameterized queries (no SQL injection)
- File upload validation
- Input validation on all endpoints
- Admin action audit trails

## Technology Stack

### Backend
- Django 4.2.8
- Django REST Framework 3.14.0
- PostgreSQL (production) / SQLite (development)
- Celery 5.3.4 (async tasks)
- Redis 5.0.1 (caching, message queue)
- Stripe 7.4.0 (payment processing)
- Pillow 10.1.0 (image processing)

### Frontend
- React 18.2.0
- React Router 6.20.0
- Axios 1.6.2 (HTTP client)

### Infrastructure
- Gunicorn (WSGI server)
- Nginx (reverse proxy)
- Docker (containerization)
- GitHub (version control)

## API Endpoints

### Authentication
- `POST /api/token/` - Obtain JWT token
- `POST /api/token/refresh/` - Refresh token
- `POST /api/users/register/` - Register new user

### Users & Profiles
- `GET /api/users/me/` - Current user info
- `GET /api/profiles/my_profile/` - User profile details
- `PATCH /api/profiles/{id}/` - Update profile

### Products
- `GET /api/products/` - List products (with search/filter)
- `GET /api/products/{id}/` - Product details
- `POST /api/products/` - Create product (sellers only)
- `GET /api/products/my_products/` - My products (sellers only)
- `POST /api/reviews/create_review/` - Post review

### Shopping
- `GET /api/cart/my_cart/` - Get cart
- `POST /api/cart/add_item/` - Add to cart
- `POST /api/cart/remove_item/` - Remove from cart

### Orders
- `POST /api/orders/checkout/` - Create order
- `GET /api/orders/my_orders/` - Order history
- `POST /api/orders/{id}/confirm_order/` - Confirm order (admin)

### Returns & Cancellations
- `POST /api/returns/request_return/` - Request return
- `GET /api/returns/` - List returns
- `POST /api/cancellations/request_cancellation/` - Request cancellation
- `POST /api/cancellations/{id}/approve/` - Approve cancellation (admin)

### Messaging
- `POST /api/messages/send_message/` - Send message
- `GET /api/messages/inbox/` - Get inbox
- `POST /api/messages/mark_as_read/` - Mark message as read

### Chatbot
- `POST /api/chatbot/chat/` - Chat with bot

### Stores
- `GET /api/stores/` - List stores
- `GET /api/stores/my_store/` - My store (sellers only)

## Setup Time

- **Backend**: ~5 minutes (pip install, migrate, runserver)
- **Frontend**: ~2 minutes (npm install, npm start)
- **Full setup**: ~10 minutes

See `QUICKSTART.md` for detailed setup instructions.

## Testing

Basic test cases included in `core/tests.py`:
- User registration
- Password validation
- Product creation
- Search functionality
- Cart operations

Run tests:
```bash
python manage.py test
```

## Documentation

- `README.md` - Main documentation, features, security audit
- `QUICKSTART.md` - 10-minute setup guide
- `DEPLOYMENT.md` - Production deployment instructions
- `SECURITY.md` - Comprehensive security audit by module
- `PROJECT_STRUCTURE.md` - This file

## Next Steps

1. **Stripe Payment Integration**: Add real payment processing
2. **Image Upload UI**: Product and profile image uploads
3. **Celery Tasks**: Email notifications, async order processing
4. **Advanced Search**: Elasticsearch or similar
5. **Real Chatbot**: Integrate OpenAI or Anthropic API
6. **Mobile App**: React Native version
7. **Analytics**: Advanced reporting with charts
8. **Notifications**: Real-time updates with WebSockets
9. **Compliance**: GDPR, CCPA implementation
10. **Testing**: Comprehensive test coverage

## Support & Maintenance

- Regular security updates (monthly)
- Dependency updates (as needed)
- Monitoring and logging (Sentry, DataDog)
- Database backups (daily)
- Load testing before scaling

See `SECURITY.md` for production security checklist.
