import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import config_by_name

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address)

def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    CORS(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.customer import customer_bp
    from app.routes.seller import seller_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.chatbot import chatbot_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(customer_bp, url_prefix="/customer")
    app.register_blueprint(seller_bp, url_prefix="/seller")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(chatbot_bp, url_prefix="/chatbot")

    return app
