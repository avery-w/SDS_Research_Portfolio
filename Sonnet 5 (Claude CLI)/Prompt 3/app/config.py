from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str
    environment: str = "development"
    session_cookie_secure: bool = False

    database_url: str

    ups_client_id: str = ""
    ups_client_secret: str = ""
    ups_account_number: str = ""
    ups_env: str = "sandbox"

    anthropic_api_key: str = ""

    max_upload_mb: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
