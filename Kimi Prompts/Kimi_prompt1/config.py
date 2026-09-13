"""Application configuration.

Every value can be overridden with an environment variable so that the same
code base runs against SQLite in development and PostgreSQL in production
without a source change.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_INSTANCE_PATH = PROJECT_ROOT / "instance"
DEFAULT_UPLOAD_PATH = DEFAULT_INSTANCE_PATH / "uploads"

# Load .env from the project root (a no-op when the file is absent).
load_dotenv(PROJECT_ROOT / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


class BaseConfig:
    """Settings shared by every environment."""

    APP_NAME = os.environ.get("APP_NAME", "Mercado Marketplace")
    APP_TAGLINE = "A marketplace where small shops ship fast."
    APP_VERSION = "1.0.0"

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    PREFERRED_URL_SCHEME = os.environ.get("PREFERRED_URL_SCHEME", "http")

    # -- Database ----------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{(DEFAULT_INSTANCE_PATH / 'marketplace.db').as_posix()}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "future": True}
    DB_POOL_RECYCLE_SECONDS = _env_int("DB_POOL_RECYCLE_SECONDS", 280)

    # -- Sessions / cookies -----------------------------------------------
    SESSION_COOKIE_NAME = "mercado_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # -- CSRF --------------------------------------------------------------
    WTF_CSRF_ENABLED = _env_bool("WTF_CSRF_ENABLED", True)
    WTF_CSRF_TIME_LIMIT = None  # tokens live as long as the session

    # -- Uploads -----------------------------------------------------------
    MAX_CONTENT_LENGTH = _env_int("MAX_CONTENT_LENGTH_MB", 8) * 1024 * 1024
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(DEFAULT_UPLOAD_PATH))
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
    ALLOWED_IMAGE_MIMETYPES = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    }
    PRODUCT_IMAGE_MAX_EDGE = 1600
    PRODUCT_THUMBNAIL_EDGE = 480
    PRODUCT_IMAGE_QUALITY = 86

    # -- Money / commerce --------------------------------------------------
    CURRENCY = "USD"
    CURRENCY_SYMBOL = "$"
    DEFAULT_TAX_RATE = _env_float("DEFAULT_TAX_RATE", 0.0825)  # Austin, TX
    DEFAULT_COMMISSION_RATE = _env_float("DEFAULT_COMMISSION_RATE", 0.08)
    FREE_SHIPPING_THRESHOLD_CENTS = _env_int("FREE_SHIPPING_THRESHOLD_CENTS", 7500)

    # -- UPS rating --------------------------------------------------------
    UPS_ENABLED = _env_bool("UPS_ENABLED", False)
    UPS_CLIENT_ID = os.environ.get("UPS_CLIENT_ID", "")
    UPS_CLIENT_SECRET = os.environ.get("UPS_CLIENT_SECRET", "")
    UPS_ACCOUNT_NUMBER = os.environ.get("UPS_ACCOUNT_NUMBER", "")
    UPS_BASE_URL = os.environ.get("UPS_BASE_URL", "https://onlinetools.ups.com")
    UPS_TIMEOUT_SECONDS = _env_float("UPS_TIMEOUT_SECONDS", 6.0)
    UPS_REQUEST_OPTION = os.environ.get("UPS_REQUEST_OPTION", "Shop")
    UPS_RATE_LIMIT_PER_HOUR = _env_int("UPS_RATE_LIMIT_PER_HOUR", 240)

    # UPS origin: 110 Inner Campus Drive, Austin, TX 78705
    UPS_ORIGIN_NAME = os.environ.get("UPS_ORIGIN_NAME", "Mercado Fulfillment Hub")
    UPS_ORIGIN_STREET = os.environ.get("UPS_ORIGIN_STREET", "110 Inner Campus Drive")
    UPS_ORIGIN_CITY = os.environ.get("UPS_ORIGIN_CITY", "Austin")
    UPS_ORIGIN_STATE = os.environ.get("UPS_ORIGIN_STATE", "TX")
    UPS_ORIGIN_POSTAL_CODE = os.environ.get("UPS_ORIGIN_POSTAL_CODE", "78705")
    UPS_ORIGIN_COUNTRY = os.environ.get("UPS_ORIGIN_COUNTRY", "US")
    UPS_ORIGIN_PHONE = os.environ.get("UPS_ORIGIN_PHONE", "5125551200")

    # UPS published/retail accessorial values used by the modeled engine.
    UPS_FUEL_SURCHARGE_RATE = _env_float("UPS_FUEL_SURCHARGE_RATE", 0.1475)
    UPS_RESIDENTIAL_SURCHARGE_CENTS = _env_int(
        "UPS_RESIDENTIAL_SURCHARGE_CENTS", 660
    )
    UPS_DELIVERY_AREA_SURCHARGE_CENTS = _env_int(
        "UPS_DELIVERY_AREA_SURCHARGE_CENTS", 625
    )
    UPS_EXTENDED_DELIVERY_AREA_SURCHARGE_CENTS = _env_int(
        "UPS_EXTENDED_DELIVERY_AREA_SURCHARGE_CENTS", 1010
    )
    UPS_ADDITIONAL_HANDLING_CENTS = _env_int("UPS_ADDITIONAL_HANDLING_CENTS", 2400)
    UPS_LARGE_PACKAGE_CENTS = _env_int("UPS_LARGE_PACKAGE_CENTS", 13000)
    UPS_OVER_MAX_LIMIT_CENTS = _env_int("UPS_OVER_MAX_LIMIT_CENTS", 22000)
    UPS_SIGNATURE_REQUIRED_CENTS = _env_int("UPS_SIGNATURE_REQUIRED_CENTS", 720)
    UPS_ADULT_SIGNATURE_CENTS = _env_int("UPS_ADULT_SIGNATURE_CENTS", 830)
    UPS_SATURDAY_DELIVERY_CENTS = _env_int("UPS_SATURDAY_DELIVERY_CENTS", 2100)
    UPS_INSURANCE_PER_100_CENTS = _env_int("UPS_INSURANCE_PER_100_CENTS", 105)
    UPS_DIM_DIVISOR = _env_int("UPS_DIM_DIVISOR", 139)
    UPS_MAX_PACKAGE_WEIGHT_LB = _env_int("UPS_MAX_PACKAGE_WEIGHT_LB", 150)
    UPS_MAX_LENGTH_IN = _env_int("UPS_MAX_LENGTH_IN", 108)
    UPS_MAX_LENGTH_PLUS_GIRTH_IN = _env_int("UPS_MAX_LENGTH_PLUS_GIRTH_IN", 165)
    UPS_QUOTE_TTL_MINUTES = _env_int("UPS_QUOTE_TTL_MINUTES", 45)
    UPS_INCLUDE_SATURDAY = _env_bool("UPS_INCLUDE_SATURDAY", False)

    # -- Chatbot -----------------------------------------------------------
    CHATBOT_ENABLED = _env_bool("CHATBOT_ENABLED", True)
    CHATBOT_MODEL = os.environ.get("CHATBOT_MODEL", "gpt-4o-mini")
    CHATBOT_MAX_TOKENS = _env_int("CHATBOT_MAX_TOKENS", 480)
    CHATBOT_TEMPERATURE = _env_float("CHATBOT_TEMPERATURE", 0.4)
    CHATBOT_HISTORY_TURNS = _env_int("CHATBOT_HISTORY_TURNS", 12)
    CHATBOT_RATE_LIMIT_PER_MINUTE = _env_int("CHATBOT_RATE_LIMIT_PER_MINUTE", 30)
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "")

    # -- Mail --------------------------------------------------------------
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = _env_int("MAIL_PORT", 587)
    MAIL_USE_TLS = _env_bool("MAIL_USE_TLS", True)
    MAIL_USE_SSL = _env_bool("MAIL_USE_SSL", False)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", "no-reply@mercado.local"
    )
    MAIL_SUPPRESS_SEND = _env_bool("MAIL_SUPPRESS_SEND", True)

    # -- Pagination --------------------------------------------------------
    PRODUCTS_PER_PAGE = _env_int("PRODUCTS_PER_PAGE", 12)
    ORDERS_PER_PAGE = _env_int("ORDERS_PER_PAGE", 15)
    ADMIN_PER_PAGE = _env_int("ADMIN_PER_PAGE", 25)

    # -- Rate limiting -----------------------------------------------------
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_DEFAULT = ["2000 per hour", "300 per minute"]

    # -- Misc --------------------------------------------------------------
    SEED_DEMO_DATA = _env_bool("SEED_DEMO_DATA", True)
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    JSON_SORT_KEYS = False
    TEMPLATES_AUTO_RELOAD = _env_bool("TEMPLATES_AUTO_RELOAD", False)


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    SQLALCHEMY_ECHO = _env_bool("SQLALCHEMY_ECHO", False)


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS = {"future": True}
    RATELIMIT_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    SERVER_NAME = "localhost"
    SEED_DEMO_DATA = False
    SECRET_KEY = "testing-secret-key"


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", True)
    PREFERRED_URL_SCHEME = "https"
    MAIL_SUPPRESS_SEND = _env_bool("MAIL_SUPPRESS_SEND", False)


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(name: str | None = None):
    """Return the config class for ``name`` (falls back to development)."""

    key = (name or os.environ.get("FLASK_ENV") or "development").strip().lower()
    return CONFIG_MAP.get(key, DevelopmentConfig)
