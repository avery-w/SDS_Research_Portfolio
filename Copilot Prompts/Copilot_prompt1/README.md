# Northstar Market

A full-stack Flask e-commerce marketplace with SQLite persistence, role-aware customer/seller/admin workspaces, checkout shipping rates, product search, image uploads, and an AI-style customer concierge.

## Run locally

```powershell
cd "Copilot Prompts/Copilot_prompt1"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

Demo accounts:

- Customer: `customer@example.com` / `customer`
- Seller: `seller@example.com` / `seller`
- Admin: `admin@example.com` / `admin`

The SQLite database is created automatically as `marketplace.db`. Set `MARKETPLACE_SECRET` in production. Checkout uses a transparent UPS Ground estimate from `110 Inner Campus Drive, Austin, TX 78705`; orders of $75 or more receive free ground shipping.

Every JSON endpoint returns a clear 4xx response for malformed or missing input, requires authentication where appropriate, and checks the current role and resource ownership before mutation.
