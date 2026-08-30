import os
from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlmodel import SQLModel, Field, Relationship


class UserRole(str, Enum):
    CUSTOMER = "customer"
    SELLER = "seller"
    ADMIN = "admin"


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    full_name: str
    role: UserRole = UserRole.CUSTOMER
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    stores: List["Store"] = Relationship(back_populates="owner")
    cart_items: List["CartItem"] = Relationship(back_populates="user")
    orders: List["Order"] = Relationship(back_populates="user")
    sent_messages: List["Message"] = Relationship(
        back_populates="sender", sa_relationship_kwargs={"foreign_keys": "Message.sender_id"}
    )
    received_messages: List["Message"] = Relationship(
        back_populates="receiver", sa_relationship_kwargs={"foreign_keys": "Message.receiver_id"}
    )


class Store(SQLModel, table=True):
    __tablename__ = "stores"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    owner_id: int = Field(foreign_key="users.id", index=True)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    owner: User = Relationship(back_populates="stores")
    products: List["Product"] = Relationship(back_populates="store")
    orders: List["Order"] = Relationship(back_populates="store")


class Product(SQLModel, table=True):
    __tablename__ = "products"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    price: float
    stock: int
    image_url: Optional[str] = None
    store_id: int = Field(foreign_key="stores.id", index=True)
    category: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    store: Store = Relationship(back_populates="products")
    cart_items: List["CartItem"] = Relationship(back_populates="product")
    order_items: List["OrderItem"] = Relationship(back_populates="product")


class CartItem(SQLModel, table=True):
    __tablename__ = "cart_items"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    quantity: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: User = Relationship(back_populates="cart_items")
    product: Product = Relationship(back_populates="cart_items")


class Order(SQLModel, table=True):
    __tablename__ = "orders"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    store_id: int = Field(foreign_key="stores.id", index=True)
    total: float
    status: str = "pending"
    shipping_address: str
    shipping_city: str
    shipping_state: str
    shipping_zip: str
    shipping_country: str = "US"
    tracking_number: Optional[str] = None
    shipping_rate: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    user: User = Relationship(back_populates="orders")
    store: Store = Relationship(back_populates="orders")
    items: List["OrderItem"] = Relationship(back_populates="order")
    return_request: Optional["ReturnRequest"] = Relationship(back_populates="order")
    messages: List["Message"] = Relationship(back_populates="order")


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    quantity: int
    price: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

    order: Order = Relationship(back_populates="items")
    product: Product = Relationship(back_populates="order_items")


class Message(SQLModel, table=True):
    __tablename__ = "messages"
    id: Optional[int] = Field(default=None, primary_key=True)
    sender_id: int = Field(foreign_key="users.id", index=True)
    receiver_id: int = Field(foreign_key="users.id", index=True)
    order_id: Optional[int] = Field(foreign_key="orders.id", index=True)
    content: str
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    sender: User = Relationship(
        back_populates="sent_messages",
        sa_relationship_kwargs={"foreign_keys": "Message.sender_id"},
    )
    receiver: User = Relationship(
        back_populates="received_messages",
        sa_relationship_kwargs={"foreign_keys": "Message.receiver_id"},
    )
    order: Optional[Order] = Relationship(back_populates="messages")


class ReturnRequest(SQLModel, table=True):
    __tablename__ = "return_requests"
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", unique=True, index=True)
    reason: str
    status: str = "pending"
    admin_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    order: Order = Relationship(back_populates="return_request")


class PlatformSetting(SQLModel, table=True):
    __tablename__ = "platform_settings"
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True)
    value: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Analytics(SQLModel, table=True):
    __tablename__ = "analytics"
    id: Optional[int] = Field(default=None, primary_key=True)
    metric_name: str = Field(index=True)
    metric_value: float
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
