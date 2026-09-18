from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    SECRET_KEY: str = "dev-only-INSECURE-change-before-production"
    DATABASE_URL: str = "sqlite:///./marketplace.db"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"
    OPENAI_API_KEY: str | None = None
    UPLOAD_DIR: str = "uploads"
    ORIGIN_ADDRESS: str = "110 Inner Campus Drive, Austin, TX 78705"
    ORIGIN_ZIP: str = "78705"
    PLATFORM_NAME: str = "Austin Market"
    MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024
    CORS_ORIGINS: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
