import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = str(BASE_DIR / "app" / "static" / "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8MB uploads

    # Fixed warehouse / ship-from address (per spec)
    SHIP_FROM_ADDRESS = {
        "name": "Marketplace Fulfillment",
        "address": "110 Inner Campus Drive",
        "city": "Austin",
        "state": "TX",
        "zip": "78705",
        "country": "US",
    }

    UPS_CLIENT_ID = os.environ.get("UPS_CLIENT_ID")
    UPS_CLIENT_SECRET = os.environ.get("UPS_CLIENT_SECRET")
    UPS_ACCOUNT_NUMBER = os.environ.get("UPS_ACCOUNT_NUMBER")
    UPS_ENV = os.environ.get("UPS_ENV", "test")  # "test" or "production"

    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
