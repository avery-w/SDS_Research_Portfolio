# Setup Guide

## Prerequisites

- Docker & Docker Compose (recommended for local development)
- OR: Python 3.11+, Node 18+, PostgreSQL 15+

## Option 1: Docker Compose (Recommended)

### Step 1: Clone and Configure

```bash
git clone <repository>
cd ecommerce-marketplace
cp .env.example .env
```

### Step 2: Start Services

```bash
docker-compose up --build
```

First run will:
- Create PostgreSQL database
- Initialize tables
- Start backend API on port 8000
- Start frontend on port 3000

### Step 3: Verify Installation

- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Option 2: Local Development

### Backend Setup

1. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set up PostgreSQL:
```bash
# Create database and user
createdb ecommerce
createuser -P ecommerce
# When prompted for password, enter: ecommerce
```

4. Create .env file:
```bash
cp .env.example .env
```

5. Start backend:
```bash
uvicorn app.main:app --reload --port 8000
```

Backend will be available at http://localhost:8000

### Frontend Setup

1. Open new terminal, navigate to frontend:
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

Frontend will open at http://localhost:3000

## First Steps

### Create Test Users

1. **Customer Account**
   - Go to http://localhost:3000/register
   - Create account with any email
   - You're automatically a customer

2. **Seller Account**
   - Register with different email
   - Database: Change role from CUSTOMER to SELLER
   ```sql
   UPDATE users SET role = 'seller' WHERE email = 'seller@example.com';
   ```

3. **Admin Account**
   ```sql
   UPDATE users SET role = 'admin' WHERE email = 'admin@example.com';
   ```

### Create Sample Products

1. Login as seller
2. Go to Seller Dashboard
3. Create a store
4. Add products to the store
5. Logout and browse as customer

### Test Checkout Flow

1. Login as customer
2. Browse products
3. Add items to cart
4. Proceed to checkout
5. Add shipping address
6. Complete payment (uses test data)

## Database Management

### Access PostgreSQL

```bash
# From container
docker-compose exec postgres psql -U ecommerce -d ecommerce

# Or locally
psql -U ecommerce -d ecommerce
```

### Common Queries

```sql
-- View all users
SELECT id, email, role, is_active FROM users;

-- View products
SELECT id, name, price, quantity_available FROM products;

-- View orders
SELECT id, customer_id, status, total_amount FROM orders;

-- View analytics
SELECT COUNT(*) as total_users FROM users;
SELECT SUM(total_amount) as revenue FROM orders WHERE status = 'paid';
```

### Reset Database

```bash
# Via Docker
docker-compose down -v
docker-compose up --build

# Or locally
dropdb ecommerce
createdb ecommerce
python -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

## API Testing

### Using cURL

```bash
# Register
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","full_name":"Test User"}'

# Login
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test123"

# List products
curl -X GET "http://localhost:8000/products"
```

### Using Swagger UI

Visit http://localhost:8000/docs for interactive API testing

## Environment Variables

Key variables to customize:

```env
# Database
DATABASE_URL=postgresql://user:password@host:port/dbname

# Security
SECRET_KEY=your-secret-key-min-32-chars

# Third-party APIs
STRIPE_SECRET_KEY=sk_test_...
OPENAI_API_KEY=sk-...

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]
```

## Troubleshooting

### Database Connection Error
```
Error: could not connect to server
```
- Check PostgreSQL is running: `docker-compose ps`
- Verify DATABASE_URL in .env
- For local: `psql -U ecommerce -d ecommerce` to test

### Port Already in Use
```
Address already in use
```
- Change port in docker-compose.yml
- Or kill process: `lsof -i :8000` then `kill -9 <PID>`

### CORS Errors
- Frontend and backend URLs must match CORS_ORIGINS
- Default: `http://localhost:3000` and `http://localhost:8000`

### Frontend Blank Page
- Check browser console (F12) for errors
- Verify REACT_APP_API_URL is set correctly
- Backend must be running on port 8000

### Module Not Found
```bash
# Backend
pip install -r requirements.txt

# Frontend
npm install
```

## Performance Tuning

### For Production

1. Database connection pooling (already enabled)
2. Use PostgreSQL with proper indexing
3. Enable HTTPS/TLS
4. Add Redis for caching (optional)
5. Use CDN for frontend assets
6. Enable gzip compression

### Add Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
```

## Monitoring

### Log Files

```bash
# Docker logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Local
# Check console output of uvicorn and npm start
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Security Checklist

- [ ] Change SECRET_KEY in production
- [ ] Use real Stripe API keys (not test keys)
- [ ] Use real OpenAI API key
- [ ] Enable HTTPS
- [ ] Use strong database passwords
- [ ] Set CORS to allowed domains only
- [ ] Enable rate limiting
- [ ] Regular backups of database
- [ ] Monitor logs for suspicious activity

## Next Steps

1. Add email notifications for orders
2. Implement image upload storage (S3/Cloud Storage)
3. Add search filters and facets
4. Implement cart auto-save
5. Add order tracking updates via WebSocket
6. Enhance admin dashboard with charts
7. Add inventory alerts
8. Implement wishlists

## Support

For detailed API documentation, visit `/docs` endpoint
For database schema, see `app/models.py`
