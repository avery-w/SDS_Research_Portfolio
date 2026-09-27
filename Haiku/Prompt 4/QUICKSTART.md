# Quick Start (5 minutes)

## Clone & Run

```bash
# Get the code
git clone <repo-url>
cd ecommerce-marketplace

# Copy config
cp .env.example .env

# Start everything
docker-compose up --build
```

**Wait ~2-3 minutes for databases to initialize.**

## Access

- Frontend: http://localhost:3000
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

## First Test

1. Go to http://localhost:3000
2. Click Register → Create account
3. Go to Products → Browse
4. Click product → Add to cart
5. Go to Cart → Checkout
6. Add address → Place order

**Done!** You have a working marketplace.

## For Sellers

Promote your account to seller in database:

```bash
# Get container shell
docker-compose exec postgres psql -U ecommerce -d ecommerce

# In psql:
UPDATE users SET role = 'seller' WHERE email = 'your@email.com';
```

Then:
- Login
- Seller Dashboard → Create Store
- Add Products
- Manage Orders

## For Admins

```bash
# In psql:
UPDATE users SET role = 'admin' WHERE email = 'your@email.com';
```

Then:
- Admin Dashboard → View analytics
- Manage users and stores

## Next: Customize

Edit `.env` for:
- Stripe keys: `STRIPE_SECRET_KEY=sk_live_...`
- OpenAI: `OPENAI_API_KEY=sk-...`
- Database: `DATABASE_URL=postgresql://...`
- Domain: `CORS_ORIGINS=["https://yourdomain.com"]`

## Stop

```bash
docker-compose down
```

## Common Issues

**Port in use?**
```bash
docker-compose down -v
```

**Reset everything?**
```bash
docker-compose down -v
docker-compose up --build
```

**Check logs?**
```bash
docker-compose logs -f backend
```

## Docs

- README.md - Overview
- SETUP.md - Detailed setup
- API_EXAMPLES.md - API calls
- DEPLOYMENT.md - Production
- PROJECT_SUMMARY.md - Architecture

That's it! You're live. 🚀
