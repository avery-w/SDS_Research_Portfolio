from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Marketplace"
    
    # Database
    DATABASE_URL: str
    REDIS_URL: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # UPS API
    UPS_API_KEY: Optional[str] = None
    UPS_API_SECRET: Optional[str] = None
    UPS_ACCOUNT_NUMBER: Optional[str] = None
    UPS_ORIGIN_ADDRESS: str = "110 Inner Campus Drive, Austin, TX 78705"
    
    # AI API
    OPENAI_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"

settings = Settings()
