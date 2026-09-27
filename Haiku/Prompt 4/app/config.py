from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://ecommerce:ecommerce@localhost:5432/ecommerce"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    STRIPE_SECRET_KEY: str = "sk_test_placeholder"
    STRIPE_PUBLISHABLE_KEY: str = "pk_test_placeholder"

    OPENAI_API_KEY: str = "sk-placeholder"

    UPS_USERNAME: str = "test_username"
    UPS_PASSWORD: str = "test_password"
    UPS_ACCESS_LICENSE: str = "test_license"
    UPS_BASE_URL: str = "https://onlinetools.ups.com"
    WAREHOUSE_ADDRESS: str = "110 Inner Campus Drive, Austin, TX 78705"

    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
