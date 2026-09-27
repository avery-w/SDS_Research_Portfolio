# Quick Start Guide

Get the marketplace running in 10 minutes.

## Backend

### 1. Setup Python Environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Database & Environment

```bash
cp .env.example .env
# Edit .env if needed (SQLite works for dev by default)
```

### 3. Initialize Database

```bash
python manage.py makemigrations core orders
python manage.py migrate
python manage.py createsuperuser  # Create admin user
```

### 4. Load Sample Data (Optional)

```bash
python manage.py shell
```

Then in the shell:
```python
from django.contrib.auth.models import User
from core.models import UserProfile, Store, Product
from orders.models import ShippingRate

# Create a seller
seller = User.objects.create_user(username='seller@test.com', email='seller@test.com', password='SecurePass123!')
UserProfile.objects.create(user=seller, role='seller')

# Create a store
store = Store.objects.create(
    seller=seller,
    name='My Store',
    address='123 Main St',
    city='Austin',
    state='TX',
    zip_code='78701',
    country='USA'
)

# Create a product
Product.objects.create(
    store=store,
    name='Sample Product',
    description='A sample product for testing',
    price=99.99,
    stock=50,
    sku='SAMPLE001',
    category='Electronics',
    weight_kg=1.5
)

# Add shipping rate
ShippingRate.objects.create(
    carrier='UPS',
    service_type='Ground',
    base_rate=15.00,
    per_pound=0.50,
    per_mile=0.001
)

exit()
```

### 5. Run Server

```bash
python manage.py runserver
```

Access the API at `http://localhost:8000/api/`
Admin panel at `http://localhost:8000/admin/`

---

## Frontend

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start Development Server

```bash
npm start
```

Frontend runs at `http://localhost:3000`

---

## Testing the Application

### 1. Register a Customer

Navigate to `http://localhost:3000/register`
- Select "Customer" role
- Fill in email and password
- Register

### 2. Login

`http://localhost:3000/login` with your credentials

### 3. Browse Products

Visit the home page to see the sample product

### 4. Add to Cart & Checkout

- Click product
- Click "Add to Cart"
- Navigate to cart
- Click "Proceed to Checkout"
- Fill in shipping address
- Place order

### 5. View Orders

Visit "Orders" in the menu to see your order history

### 6. Register as Seller

Register with "Seller" role, then access the seller dashboard to:
- View your store
- Create new products
- View orders from your store

### 7. Admin Access

Login as superuser (created during setup) and visit:
- `http://localhost:8000/admin/` for Django admin
- Admin dashboard (frontend) for analytics

---

## Key API Endpoints to Test

```bash
# Get token
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"seller@test.com","password":"SecurePass123!"}'

# Get products
curl http://localhost:8000/api/products/

# Search products
curl 'http://localhost:8000/api/products/?search=Sample'

# Get cart (requires auth)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/cart/my_cart/
```

---

## Common Issues

### Port Already in Use
```bash
# Django (8000)
python manage.py runserver 8001

# React (3000)
PORT=3001 npm start
```

### Database Errors
```bash
# Reset database
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

### Module Not Found
```bash
pip install -r requirements.txt
npm install
```

---

## Next Steps

- Implement Stripe payment integration
- Add image uploads for products
- Deploy to production (see DEPLOYMENT.md)
- Setup Celery for async tasks
- Add more comprehensive testing
- Implement advanced search/filtering
- Add email notifications
- Setup monitoring and logging

See README.md and DEPLOYMENT.md for full documentation.
