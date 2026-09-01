from pydantic_settings import BaseSettings
from pydantic import AnyUrl, SecretStr
from typing import Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Marketplace"
    ENV: str = "dev"
    API_V1_PREFIX: str = "/api"
    ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # DB
    DATABASE_URL: AnyUrl

    # Security
    SECRET_KEY: SecretStr
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # Storage
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[SecretStr] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_REGION: Optional[str] = None
    MEDIA_BASE_URL: Optional[str] = None  # fallback if not using S3

    # UPS
    UPS_CLIENT_ID: Optional[str] = None
    UPS_CLIENT_SECRET: Optional[SecretStr] = None
    UPS_ACCOUNT_NUMBER: Optional[str] = None
    UPS_ENV: str = "sandbox"  # "sandbox" or "prod"

    # Chatbot
    OPENAI_API_KEY: Optional[SecretStr] = None

    # Admin
    ADMIN_EMAIL: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
