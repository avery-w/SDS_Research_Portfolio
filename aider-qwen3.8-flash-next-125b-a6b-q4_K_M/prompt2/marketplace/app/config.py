import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.environ["SECRET_KEY"]
    SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "..", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    UPS_API_KEY = os.environ["UPS_API_KEY"]
    UPS_API_URL = "https://onlinetools.ups.com/api/rating/v2405/Rate"
    UPS_ORIGIN_ZIP = "78705"
    UPS_ORIGIN_ADDRESS = "110 Inner Campus Drive, Austin, TX 78705"
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
    STRIPE_SECRET_KEY = os.environ["STRIPE_SECRET_KEY"]
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
