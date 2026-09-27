from flask import Flask
from app.extensions import db, login_manager, migrate, cache

def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    login_manager.login_view = "auth.login"

    from app.routes.auth import bp as auth_bp
    from app.routes.customer import bp as customer_bp
    from app.routes.seller import bp as seller_bp
    from app.routes.admin import bp as admin_bp
    from app.routes.checkout import bp as checkout_bp
    from app.routes.chatbot import bp as chatbot_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(seller_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(checkout_bp)
    app.register_blueprint(chatbot_bp)
    return app
