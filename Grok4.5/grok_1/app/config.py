from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    SECRET_KEY: str = "dev-secret-change-in-production-use-a-long-random-string"
    DATABASE_URL: str = "sqlite:///./marketplace.db"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALGORITHM: str = "HS256"
    OPENAI_API_KEY: str | None = None
    UPLOAD_DIR: str = "uploads"
    ORIGIN_ADDRESS: str = "110 Inner Campus Drive, Austin, TX 78705"
    ORIGIN_ZIP: str = "78705"
    # Platform defaults (overridable by admin later)
    PLATFORM_NAME: str = "Austin Market"
    DEFAULT_CURRENCY: str = "USD"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
