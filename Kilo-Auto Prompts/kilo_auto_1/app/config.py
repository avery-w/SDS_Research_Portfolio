"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- General ---
    app_name: str = "Kilo Marketplace"
    app_env: str = "development"

    @field_validator("debug", mode="before")
    @classmethod
    def _coerce_debug(cls, v: object) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(v)
        if isinstance(v, str):
            return v.strip().lower() in ("true", "1", "yes", "debug", "on")
        return bool(v)

    debug: bool = Field(default=True, validation_alias="APP_DEBUG")

    # --- Auth / JWT ---
    secret_key: str = Field(
        default="dev-secret-key-change-me",
        validation_alias="SECRET_KEY",
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./marketplace.db"

    # --- Redis / Celery ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Chatbot ---
    openai_api_key: str | None = None
    chatbot_fallback_model: str = "gpt-4o-mini"

    # --- UPS Shipping ---
    ups_origin_address: str = "110 Inner Campus Drive"
    ups_origin_city: str = "Austin"
    ups_origin_state: str = "TX"
    ups_origin_zip: str = "78705"
    ups_origin_country: str = "US"
    ups_fuel_surcharge_rate: float = 0.078
    ups_residential_surcharge: float = 4.20
    ups_min_charge_ground: float = 6.50

    # --- Uploads ---
    upload_dir: str = "app/static/uploads"
    max_upload_size: int = 5_242_880  # 5 MB

    @property
    def db_path(self) -> str:
        """Return the filesystem path to the SQLite DB file."""
        if self.database_url.startswith("sqlite:///"):
            rel = self.database_url[len("sqlite:///"):]
            return str(BASE_DIR / rel)
        return ""

    @property
    def uploads_path(self) -> Path:
        return BASE_DIR / self.upload_dir


settings = Settings()
