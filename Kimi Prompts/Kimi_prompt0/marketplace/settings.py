"""
Django settings for the SDS Research Portfolio marketplace project.

This is a modern e-commerce marketplace supporting three roles:
customer, seller, and admin. Configuration values can be overridden
through environment variables (see .env.example).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from a .env file if present.
load_dotenv(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-change-me-in-production-6qL0xY1pS8mNzK2V",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = os.getenv(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"
).split(",")

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    # Local apps
    "accounts",
    "stores",
    "catalog",
    "carts",
    "orders",
    "shipping",
    "messaging",
    "chatbot",
    "analytics",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "marketplace.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "marketplace.wsgi.application"
ASGI_APPLICATION = "marketplace.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# Defaults to SQLite for zero-configuration local development. Point
# DATABASE_URL at Postgres/MySQL in production.
if os.getenv("DATABASE_URL"):
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.config(
            default=os.getenv("DATABASE_URL"), conn_max_age=600
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Use the custom user model for role-based accounts.
AUTH_USER_MODEL = "accounts.User"

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "America/Chicago")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default auto field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

# ---------------------------------------------------------------------------
# Media / upload limits
# ---------------------------------------------------------------------------
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ---------------------------------------------------------------------------
# Marketplace specific settings
# ---------------------------------------------------------------------------
# The fixed origin warehouse/starting location for shipping rate quotes.
SHIPPING_ORIGIN_ADDRESS = os.getenv(
    "SHIPPING_ORIGIN_ADDRESS",
    "110 Inner Campus Drive",
)
SHIPPING_ORIGIN_CITY = os.getenv("SHIPPING_ORIGIN_CITY", "Austin")
SHIPPING_ORIGIN_STATE = os.getenv("SHIPPING_ORIGIN_STATE", "TX")
SHIPPING_ORIGIN_POSTAL = os.getenv("SHIPPING_ORIGIN_POSTAL", "78705")
SHIPPING_ORIGIN_COUNTRY = os.getenv("SHIPPING_ORIGIN_COUNTRY", "US")

# UPS credentials. Leave blank to use the built-in UPS-spec compliant
# rate calculator (no external network calls required).
UPS_CLIENT_ID = os.getenv("UPS_CLIENT_ID", "")
UPS_CLIENT_SECRET = os.getenv("UPS_CLIENT_SECRET", "")
UPS_API_BASE_URL = os.getenv(
    "UPS_API_BASE_URL", "https://onlinetools.ups.com"
)

# AI chatbot settings. Supports OpenAI-compatible endpoints, but falls back
# to a deterministic, intent-based assistant when no key is configured.
CHATBOT_OPENAI_API_KEY = os.getenv("CHATBOT_OPENAI_API_KEY", "")
CHATBOT_OPENAI_MODEL = os.getenv("CHATBOT_OPENAI_MODEL", "gpt-4o-mini")
CHATBOT_OPENAI_BASE_URL = os.getenv(
    "CHATBOT_OPENAI_BASE_URL", "https://api.openai.com/v1"
)
