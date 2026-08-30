import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'longcat2-marketplace-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'marketplace.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    ORIGIN_ADDRESS = {
        'street': '110 Inner Campus Drive',
        'city': 'Austin',
        'state': 'TX',
        'zip': '78705',
        'country': 'US'
    }

    UPS_API_KEY = os.environ.get('UPS_API_KEY') or ''
    UPS_API_URL = 'https://onlinetools.ups.com/api'
    UPS_USE_MOCK = os.environ.get('UPS_USE_MOCK', 'true').lower() == 'true'

    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') or ''
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL') or 'gpt-3.5-turbo'

    ITEMS_PER_PAGE = 12
    SHIPPING_BASE_RATE = 5.99
    SHIPPING_PER_ITEM = 2.50
    FREE_SHIPPING_THRESHOLD = 75.00
    TAX_RATE = 0.0825

    PLATFORM_NAME = 'LongCat Marketplace'
    PLATFORM_FEE_PERCENT = 5.0
    SUPPORT_EMAIL = 'support@longcatmarketplace.com'
