# Marketplace Backend

## Setup Instructions

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   Create a `.env` file based on `.env.example` and fill in your credentials:
   - `DATABASE_URL`: PostgreSQL connection string.
   - `JWT_SECRET`: A secure random string for JWT signing.
   - `UPS_API_KEY`: Your UPS API credentials.
   - `OPENAI_API_KEY`: Your OpenAI API key.

3. **Database Migration**:
   This initial version uses `Base.metadata.create_all(bind=engine)` for simplicity. For production, it is recommended to use Alembic.

4. **Start the Server**:
   ```bash
   uvicorn app.main:app --reload
   ```

## Architecture Overview
- **FastAPI**: Async API framework.
- **SQLAlchemy**: ORM for PostgreSQL.
- **RBAC**: Role-based access control via JWT.
- **UPS Integration**: Shipping calculation service with fallback logic.
- **AI Chatbot**: OpenAI-powered assistant with product context.
