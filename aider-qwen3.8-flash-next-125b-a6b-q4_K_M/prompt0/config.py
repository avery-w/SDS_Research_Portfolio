import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///marketplace.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "./app/static/uploads")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    UPS_API_KEY = os.getenv("UPS_API_KEY", "")
    UPS_API_USERNAME = os.getenv("UPS_API_USERNAME", "")
    UPS_API_PASSWORD = os.getenv("UPS_API_PASSWORD", "")
    UPS_ACCESS_KEY = os.getenv("UPS_ACCESS_KEY", "")
    UPS_ORIGIN_ADDRESS = {
        "street": "110 Inner Campus Drive",
        "city": "Austin",
        "state": "TX",
        "zip": "78705",
        "country": "US",
    }

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
