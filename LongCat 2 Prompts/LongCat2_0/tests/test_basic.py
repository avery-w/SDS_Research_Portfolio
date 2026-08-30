import pytest
from app import create_app, db
from app.models import User, Store, Category, Product, Order, CartItem
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    UPS_USE_MOCK = True


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_data(app):
    with app.app_context():
        admin = User(email='admin@test.com', first_name='Admin', last_name='User', role='admin')
        admin.set_password('password123')
        db.session.add(admin)

        seller = User(email='seller@test.com', first_name='Seller', last_name='User', role='seller')
        seller.set_password('password123')
        db.session.add(seller)
        db.session.flush()

        store = Store(name='Test Store', seller_id=seller.id, is_approved=True)
        db.session.add(store)

        customer = User(email='customer@test.com', first_name='Customer', last_name='User', role='customer')
        customer.set_password('password123')
        db.session.add(customer)

        category = Category(name='Electronics', slug='electronics')
        db.session.add(category)
        db.session.flush()

        product = Product(
            name='Test Product', slug='test-product',
            description='A test product', price=29.99,
            quantity=10, store_id=store.id, category_id=category.id
        )
        db.session.add(product)
        db.session.commit()

        return {
            'admin': admin,
            'seller': seller,
            'customer': customer,
            'store': store,
            'category': category,
            'product': product
        }


class TestAuth:
    def test_register(self, client):
        response = client.post('/register', data={
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'customer'
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_login(self, client, sample_data):
        response = client.post('/login', data={
            'email': 'customer@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_logout(self, client, sample_data):
        client.post('/login', data={
            'email': 'customer@test.com',
            'password': 'password123'
        })
        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200


class TestProducts:
    def test_product_listing(self, client, sample_data):
        response = client.get('/products')
        assert response.status_code == 200

    def test_product_detail(self, client, sample_data):
        response = client.get('/product/test-product')
        assert response.status_code == 200

    def test_search_products(self, client, sample_data):
        response = client.get('/products?q=Test')
        assert response.status_code == 200


class TestCart:
    def test_add_to_cart(self, client, sample_data):
        client.post('/login', data={
            'email': 'customer@test.com',
            'password': 'password123'
        })
        response = client.post(f'/customer/cart/add/{sample_data["product"].id}',
                               data={'quantity': 1}, follow_redirects=True)
        assert response.status_code == 200

    def test_cart_view(self, client, sample_data):
        client.post('/login', data={
            'email': 'customer@test.com',
            'password': 'password123'
        })
        response = client.get('/customer/cart')
        assert response.status_code == 200


class TestAPI:
    def test_api_products(self, client, sample_data):
        response = client.get('/api/products')
        assert response.status_code == 200
        data = response.get_json()
        assert 'products' in data

    def test_api_product_detail(self, client, sample_data):
        response = client.get('/api/product/test-product')
        assert response.status_code == 200

    def test_api_categories(self, client, sample_data):
        response = client.get('/api/categories')
        assert response.status_code == 200


class TestShipping:
    def test_shipping_rate_calculation(self, client, sample_data):
        from app.services.shipping import ShippingService
        service = ShippingService()
        rate = service.calculate_rate(
            weight=2.5,
            destination_zip='10001',
            destination_city='New York',
            destination_state='NY',
            method='ground'
        )
        assert 'rate' in rate
        assert rate['rate'] > 0

    def test_api_shipping_calculation(self, client, sample_data):
        client.post('/login', data={
            'email': 'customer@test.com',
            'password': 'password123'
        })
        response = client.post('/api/checkout/calculate-shipping', json={
            'weight': 2.5,
            'destination_zip': '10001',
            'destination_city': 'New York',
            'destination_state': 'NY',
            'method': 'ground'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'rate' in data
