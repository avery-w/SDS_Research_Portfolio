import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_register_and_login():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User",
            "role": "customer",
        })
        assert reg.status_code == 201

        login = await client.post("/api/auth/login", data={
            "username": "test@example.com",
            "password": "password123",
        })
        assert login.status_code == 200
        assert "access_token" in login.json()


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/auth/login", data={
            "username": "nonexistent@example.com",
            "password": "wrong",
        })
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401
