"""Test fixtures for the marketplace."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import User, UserRole, Store, Product
from app.security import hash_password

# Ensure kilo_auto_1 is on the path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_DEBUG", "true")

# Use a fresh SQLite DB per test
TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    """Create a test database engine."""
    _engine = create_async_engine(TEST_DB, echo=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    await _engine.dispose()


@pytest.fixture(scope="function")
async def session(engine):
    """Create a test database session."""
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as sess:
        yield sess
        await sess.rollback()


@pytest.fixture(scope="function")
async def db(session):
    """Alias for session."""
    yield session


@pytest.fixture(scope="function")
async def admin_user(db) -> User:
    """Create an admin user."""
    user = User(
        email="admin@test.com",
        password_hash=hash_password("adminpass123"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture(scope="function")
async def seller_user(db) -> User:
    """Create a seller user with a store."""
    user = User(
        email="seller@test.com",
        password_hash=hash_password("sellerpass123"),
        full_name="Seller User",
        role=UserRole.SELLER,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    store = Store(
        seller_id=user.id,
        name="Test Store",
        slug="test-store",
        description="A test store",
    )
    db.add(store)
    await db.commit()
    await db.refresh(store)

    user.store = store
    await db.refresh(user)
    return user


@pytest.fixture(scope="function")
async def customer_user(db) -> User:
    """Create a customer user."""
    user = User(
        email="customer@test.com",
        password_hash=hash_password("customerpass123"),
        full_name="Customer User",
        role=UserRole.CUSTOMER,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture(scope="function")
async def sample_product(seller_user, db) -> Product:
    """Create a sample product."""
    product = Product(
        store_id=seller_user.store.id,
        name="Test Widget",
        slug="test-widget",
        description="A test widget",
        price=29.99,
        cost_price=15.00,
        sku="TW-001",
        stock_quantity=100,
        is_active=True,
        weight=2.5,
        length=10,
        width=8,
        height=6,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product
