from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Marketplace API"
    SECRET_KEY: str = "SUPER_SECRET_KEY_CHANGE_ME_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    DATABASE_URL: str = "postgresql://user:password@localhost/marketplace"
    
    OPENAI_API_KEY: Optional[str] = None
    UPS_API_KEY: Optional[str] = None
    UPS_ACCOUNT_NUMBER: Optional[str] = None
    
    UPS_ORIGIN_ADDRESS: str = "110 Inner Campus Drive, Austin, TX 78705"

    class Config:
        env_file = ".env"

settings = Settings()
