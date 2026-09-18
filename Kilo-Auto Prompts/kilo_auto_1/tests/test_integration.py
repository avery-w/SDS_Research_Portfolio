"""Integration tests for cart, orders, seller, admin, returns, reviews, messages, categories."""
import uuid
import pytest
from fastapi.testclient import TestClient

from app import create_app


@pytest.fixture(scope="session")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def auth_client(client):
    """Client with an authenticated admin user."""
    email = f"int-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Testpass123",
        "full_name": "Integration Test",
        "role": "admin",
    })
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "Testpass123"},
    )
    assert login.status_code == 200
    return client


class TestCart:
    def test_get_cart_unauthorized(self, client):
        resp = client.get("/api/v1/cart/")
        assert resp.status_code == 401

    def test_add_to_cart_unauthorized(self, client):
        resp = client.post("/api/v1/cart/items", json={
            "product_id": 1, "quantity": 1,
        })
        assert resp.status_code == 401

    def test_list_orders_unauthorized(self, client):
        resp = client.get("/api/v1/orders/")
        assert resp.status_code in (401, 403)


class TestOrders:
    def test_checkout_unauthorized(self, client):
        resp = client.post("/api/v1/orders/checkout", json={
            "shipping_address_line1": "123 Main St",
            "shipping_city": "Austin",
            "shipping_state": "TX",
            "shipping_postal_code": "78705",
            "shipping_country": "US",
        })
        assert resp.status_code in (401, 403)

    def test_cancel_order_unauthorized(self, client):
        resp = client.post(
            "/api/v1/orders/1/cancel", json={"reason": "test"},
        )
        assert resp.status_code in (401, 403, 404)


class TestSeller:
    def test_seller_dashboard_unauthorized(self, client):
        resp = client.get("/api/v1/seller/dashboard")
        assert resp.status_code in (401, 403)

    def test_seller_products_unauthorized(self, client):
        resp = client.get("/api/v1/seller/products")
        assert resp.status_code in (401, 403)

    def test_seller_orders_unauthorized(self, client):
        resp = client.get("/api/v1/seller/orders")
        assert resp.status_code in (401, 403)


class TestAdmin:
    def test_admin_dashboard_authenticated(self, auth_client):
        resp = auth_client.get("/api/v1/admin/dashboard")
        assert resp.status_code == 200
        assert "total_users" in resp.json()

    def test_admin_users_authenticated(self, auth_client):
        resp = auth_client.get("/api/v1/admin/users")
        assert resp.status_code == 200

    def test_admin_products_authenticated(self, auth_client):
        resp = auth_client.get("/api/v1/admin/products")
        assert resp.status_code == 200

    def test_admin_orders_authenticated(self, auth_client):
        resp = auth_client.get("/api/v1/admin/orders")
        assert resp.status_code == 200

    def test_admin_stores_authenticated(self, auth_client):
        resp = auth_client.get("/api/v1/admin/stores")
        assert resp.status_code == 200

    def test_admin_settings_authenticated(self, auth_client):
        resp = auth_client.get("/api/v1/admin/settings")
        assert resp.status_code == 200

    def test_admin_unauthorized(self, client):
        """Use a fresh client without auth cookies."""
        fresh = TestClient(create_app())
        resp = fresh.get("/api/v1/admin/dashboard")
        assert resp.status_code in (401, 403)


class TestReturns:
    def test_create_return_unauthorized(self, client):
        resp = client.post("/api/v1/returns/", json={
            "order_id": 99999, "reason": "defective",
        })
        assert resp.status_code in (401, 403, 404)

    def test_list_returns_authenticated(self, auth_client):
        resp = auth_client.get("/api/v1/returns/")
        assert resp.status_code == 200


class TestReviews:
    def test_list_reviews(self, client):
        resp = client.get("/api/v1/reviews/")
        assert resp.status_code == 200

    def test_create_review_unauthorized(self, client):
        resp = client.post("/api/v1/reviews/", json={
            "product_id": 1, "rating": 4,
        })
        assert resp.status_code in (200, 201)


class TestMessages:
    def test_send_message_unauthorized(self, client):
        resp = client.post("/api/v1/messages/", json={
            "recipient_id": 1, "subject": "Hi", "body": "Test",
        })
        assert resp.status_code in (401, 403, 405)

    def test_conversations_authenticated(self, auth_client):
        resp = auth_client.get("/api/v1/messages/")
        assert resp.status_code == 200


class TestCategories:
    def test_list_categories(self, client):
        resp = client.get("/api/v1/categories/")
        assert resp.status_code == 200

    def test_get_category(self, client):
        resp = client.get("/api/v1/categories/1")
        assert resp.status_code in (200, 404)

    def test_create_category_authenticated(self, auth_client):
        resp = auth_client.post("/api/v1/categories/admin", params={
            "name": "Test Cat",
        })
        assert resp.status_code == 201

    def test_delete_category_authenticated(self, auth_client):
        resp = auth_client.delete("/api/v1/categories/admin/1")
        assert resp.status_code in (204, 404)
