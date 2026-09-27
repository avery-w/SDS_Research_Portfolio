from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/marketplace"
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REDIS_URL: str = "redis://localhost:6379/0"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = "marketplace-uploads"
    AWS_REGION: str = "us-east-1"
    OPENAI_API_KEY: str = ""
    UPS_ACCESS_KEY: str = ""
    UPS_API_KEY: str = ""
    UPS_API_PASSWORD: str = ""
    UPS_ORIGIN_ADDRESS: str = "110 Inner Campus Drive, Austin, TX 78705"
    UPS_ORIGIN_ZIP: str = "78705"
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    FRONTEND_URL: str = "http://localhost:5173"
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"


settings = Settings()
