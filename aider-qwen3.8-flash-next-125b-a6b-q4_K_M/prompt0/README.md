# E-Commerce Marketplace

## Prerequisites
- Python 3.11+
- PostgreSQL 15+ (or SQLite for dev)
- OpenAI API key (for chatbot)
- UPS API credentials (for shipping)

## Setup

1. **Clone & install dependencies**
   ```bash
   git clone <repo-url> && cd ecommerce_marketplace
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your real keys and DATABASE_URL
   ```

3. **Initialize database**
   ```bash
   flask --app run.py db init
   flask --app run.py db migrate -m "initial"
   flask --app run.py db upgrade
   ```

4. **Create admin user (run in Python shell)**
   ```bash
   flask --app run.py shell
   ```
   ```python
   from app import db
   from app.models.user import User, UserRole
   from app.models.store import Store
   admin = User(username="admin", email="admin@example.com",
                first_name="Admin", last_name="User", role=UserRole.ADMIN)
   admin.set_password("admin123")
   db.session.add(admin)
   db.session.commit()
   ```

5. **Run the server**
   ```bash
   python run.py
   ```
   Open http://localhost:5000

## Project Structure
