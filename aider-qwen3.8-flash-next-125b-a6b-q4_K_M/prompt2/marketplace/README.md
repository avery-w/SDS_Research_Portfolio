# Marketplace Setup

1. `python -m venv venv && source venv/bin/activate`
2. `pip install -r requirements.txt`
3. Copy `.env.example` → `.env`; fill in SECRET_KEY, DATABASE_URL, UPS_API_KEY, OPENAI_API_KEY, STRIPE_SECRET_KEY
4. `export FLASK_APP=run.py`
5. `flask db init && flask db migrate -m "init" && flask db upgrade`
6. `flask run`
7. Seed admin: `python -c "from app import create_app; from app.models.user import User; app=create_app(); ..."`
