import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkeychangeinproduction")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./marketplace.db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
UPS_API_KEY = os.getenv("UPS_API_KEY", "")
UPS_USERNAME = os.getenv("UPS_USERNAME", "")
UPS_PASSWORD = os.getenv("UPS_PASSWORD", "")
UPS_ACCESS_KEY = os.getenv("UPS_ACCESS_KEY", "")
UPS_ORIGIN_ZIP = "78705"
UPS_ORIGIN_ADDRESS = "110 Inner Campus Drive"
UPS_ORIGIN_CITY = "Austin"
UPS_ORIGIN_STATE = "TX"
UPS_ORIGIN_COUNTRY = "US"
UPLOAD_DIR = "uploads"
