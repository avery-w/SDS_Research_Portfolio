import os
from app import create_app, db
from app.models import User, Store, Category, Product, Order, Message, PlatformSetting

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Store': Store,
        'Category': Category,
        'Product': Product,
        'Order': Order,
        'Message': Message,
        'PlatformSetting': PlatformSetting
    }


@app.cli.command('init-db')
def init_db():
    """Initialize the database with sample data."""
    from werkzeug.security import generate_password_hash

    db.create_all()

    categories = [
        Category(name='Electronics', slug='electronics', description='Gadgets and devices', icon='laptop'),
        Category(name='Clothing', slug='clothing', description='Fashion and apparel', icon='bag'),
        Category(name='Home & Garden', slug='home-garden', description='Home essentials', icon='house'),
        Category(name='Sports', slug='sports', description='Sports and outdoor', icon='bicycle'),
        Category(name='Books', slug='books', description='Books and media', icon='book'),
        Category(name='Toys', slug='toys', description='Toys and games', icon='controller'),
    ]
    for cat in categories:
        if not Category.query.filter_by(slug=cat.slug).first():
            db.session.add(cat)

    defaults = [
        ('platform_name', 'LongCat Marketplace', 'Name of the platform'),
        ('shipping_base_rate', '5.99', 'Base shipping rate in USD'),
        ('free_shipping_threshold', '75.00', 'Free shipping threshold'),
        ('tax_rate', '0.0825', 'Sales tax rate'),
        ('platform_fee_percent', '5.0', 'Platform fee percentage'),
        ('support_email', 'support@longcatmarketplace.com', 'Support email'),
    ]
    for key, value, desc in defaults:
        if not PlatformSetting.query.filter_by(key=key).first():
            db.session.add(PlatformSetting(key=key, value=value, description=desc))

    if not User.query.filter_by(email='admin@longcat.com').first():
        admin = User(
            email='admin@longcat.com',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_active=True,
            is_verified=True
        )
        admin.set_password('admin123')
        db.session.add(admin)

    if not User.query.filter_by(email='seller@longcat.com').first():
        seller = User(
            email='seller@longcat.com',
            first_name='Jane',
            last_name='Seller',
            role='seller',
            is_active=True,
            is_verified=True
        )
        seller.set_password('seller123')
        db.session.add(seller)
        db.session.flush()
        store = Store(
            name="Jane's Boutique",
            description='Quality products at great prices',
            seller_id=seller.id,
            is_active=True,
            is_approved=True
        )
        db.session.add(store)

    if not User.query.filter_by(email='customer@longcat.com').first():
        customer = User(
            email='customer@longcat.com',
            first_name='John',
            last_name='Customer',
            role='customer',
            is_active=True,
            is_verified=True
        )
        customer.set_password('customer123')
        db.session.add(customer)

    db.session.commit()
    print('Database initialized with sample data!')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
