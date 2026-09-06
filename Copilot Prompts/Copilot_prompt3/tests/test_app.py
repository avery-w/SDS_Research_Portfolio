import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app, db

@pytest.fixture()
def client(tmp_path):
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': f'sqlite:///{tmp_path / "test.db"}', 'SECRET_KEY': 'test-secret'})
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()

def csrf(client):
    return client.get('/api/csrf').get_json()['token']

def test_register_login_and_shipping_quote(client):
    response = client.post('/api/auth/register', json={'name': 'Buyer', 'email': 'buyer@example.com', 'password': 'a-secure-password', 'role': 'customer'})
    assert response.status_code == 201
    assert client.get('/api/me').get_json()['role'] == 'customer'
    quote = client.post('/api/shipping/quote', json={'weight_lb': 2, 'length_in': 10, 'width_in': 10, 'height_in': 10, 'destination_zip': '78701'})
    assert quote.status_code == 200
    assert quote.get_json()['origin'].endswith('78705')

def test_mutation_requires_csrf(client):
    client.post('/api/auth/register', json={'name': 'Buyer', 'email': 'buyer2@example.com', 'password': 'a-secure-password', 'role': 'customer'})
    response = client.post('/api/cart/items', json={'product_id': 1, 'quantity': 1})
    assert response.status_code == 400
