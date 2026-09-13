"""Tests for authentication and API endpoints."""
from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient

from app import create_app
from app.database import AsyncSessionLocal, create_all
from app.models import User, UserRole
from app.security import hash_password


@pytest.fixture(scope="session")
def client():
    """Create a test client."""
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
async def setup_db():
    """Initialize test database."""
    await create_all()


# Helper to create a user directly in DB, bypassing the API
async def _create_user(db, email, password, full_name, role="customer"):
    from sqlalchemy import select
    user = User(
        email=email,
        password_hash=hash_password(password[:72]),
        full_name=full_name,
        role=UserRole(role),
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


class TestAuth:
    def test_register_customer(self, client):
        email = f"test-{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Testpass123",
            "full_name": "Test User",
            "role": "customer",
        })
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_register_duplicate_email(self, client):
        email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
        client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Testpass123",
            "full_name": "Dup User",
            "role": "customer",
        })
        resp = client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Testpass123",
            "full_name": "Dup User 2",
            "role": "customer",
        })
        assert resp.status_code == 409

    def test_register_weak_password(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "weak@example.com",
            "password": "123",
            "full_name": "Weak Pass",
            "role": "customer",
        })
        assert resp.status_code == 422

    def test_login_success(self, client):
        email = f"login-{uuid.uuid4().hex[:8]}@example.com"
        client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Loginpass123",
            "full_name": "Login User",
            "role": "customer",
        })
        resp = client.post("/api/v1/auth/login", data={
            "username": email,
            "password": "Loginpass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    def test_login_wrong_password(self, client):
        email = f"wrong-{uuid.uuid4().hex[:8]}@example.com"
        client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Loginpass123",
            "full_name": "Wrong",
            "role": "customer",
        })
        resp = client.post("/api/v1/auth/login", data={
            "username": email,
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_missing_password(self, client):
        resp = client.post("/api/v1/auth/login", data={
            "username": "missing@test.com",
            "password": "",
        })
        assert resp.status_code == 422

    def test_me_unauthorized(self, client):
        client.cookies.clear()
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_logout(self, client):
        email = f"logout-{uuid.uuid4().hex[:8]}@example.com"
        client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Logoutpass123",
            "full_name": "Logout",
            "role": "customer",
        })
        resp = client.post("/api/v1/auth/login", data={
            "username": email,
            "password": "Logoutpass123",
        })
        assert resp.status_code == 200
        resp2 = client.post("/api/v1/auth/logout")
        assert resp2.status_code == 200


class TestProducts:
    def test_list_products_public(self, client):
        resp = client.get("/api/v1/products/", headers={"accept": "application/json"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_product_search(self, client):
        resp = client.get("/api/v1/products/?q=widget", headers={"accept": "application/json"})
        assert resp.status_code == 200

    def test_product_detail_public(self, client):
        resp = client.get("/api/v1/products/1")
        assert resp.status_code in (200, 404)


class TestShipping:
    def test_shipping_rates(self, client):
        resp = client.post("/api/v1/shipping/rates", json={
            "weight_lbs": 2.5,
            "destination_zip": "10001",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "rates" in data
        assert "origin" in data
        assert len(data["rates"]) == 4

    def test_shipping_invalid_zip(self, client):
        resp = client.post("/api/v1/shipping/rates", json={
            "weight_lbs": 2.5,
            "destination_zip": "abc",
        })
        assert resp.status_code in (400, 422)

    def test_shipping_zero_weight(self, client):
        resp = client.post("/api/v1/shipping/rates", json={
            "weight_lbs": 0.1,
            "destination_zip": "10001",
        })
        assert resp.status_code == 200
        assert resp.json()["package"]["billable_weight_lbs"] >= 1.0
