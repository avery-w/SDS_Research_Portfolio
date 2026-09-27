from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_ENV: Literal["dev", "staging", "prod"] = "dev"
    DATABASE_URL: str = "postgresql+asyncpg://app:password@db:5432/marketplace"
    REDIS_URL: str = "redis://:password@redis:6379/0"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    UPS_CLIENT_ID: str = ""
    UPS_CLIENT_SECRET: str = ""
    UPS_ORIGIN_ADDRESS: str = "110 Inner Campus Drive, Austin, TX 78705"
    OPENAI_API_KEY: str = ""
    S3_BUCKET: str = "marketplace-media"
    S3_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    RATE_LIMIT_PER_MIN: int = 100
    MAX_UPLOAD_SIZE_MB: int = 10
    SENTRY_DSN: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
