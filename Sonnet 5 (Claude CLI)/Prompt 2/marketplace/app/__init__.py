import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    csrf.init_app(app)

    from app import models  # noqa: F401  (registers models on db metadata)
    from app.auth import auth_bp
    from app.customer import customer_bp
    from app.seller import seller_bp
    from app.admin import admin_bp
    from app.shipping import shipping_bp
    from app.chatbot import chatbot_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(seller_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(shipping_bp)
    app.register_blueprint(chatbot_bp)

    # Pure JSON APIs (no HTML form), called via fetch: exempt from CSRF form-token
    # checks. Neither endpoint mutates another user's data (shipping is a stateless
    # calculator; chatbot only reads the logged-in user's own orders).
    csrf.exempt(shipping_bp)
    csrf.exempt(chatbot_bp)

    with app.app_context():
        db.create_all()

    return app
