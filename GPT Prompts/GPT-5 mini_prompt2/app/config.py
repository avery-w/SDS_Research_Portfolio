import os
from pathlib import Path

from dotenv import load_dotenv

base_dir = Path(__file__).resolve().parent.parent
load_dotenv(base_dir / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///" + str(base_dir / "marketplace.db"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = str(base_dir / "app" / "static" / "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPS_ORIGIN_ADDRESS = os.getenv("UPS_ORIGIN_ADDRESS", "110 Inner Campus Drive, Austin, TX 78705")
