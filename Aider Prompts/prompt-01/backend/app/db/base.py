from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Import models here so Alembic can autogenerate
from app.models.user import User, Address, Role  # noqa: F401,E402
from app.models.seller import SellerProfile, Store  # noqa: F401,E402
from app.models.product import Product, ProductImage, Inventory, Category  # noqa: F401,E402
from app.models.order import Order, OrderItem, Shipment, OrderStatus, ShipmentStatus  # noqa: F401,E402
from app.models.cart import Cart, CartItem  # noqa: F401,E402
from app.models.messaging import Conversation, Message, ParticipantRole  # noqa: F401,E402
from app.models.returns import ReturnRequest, ReturnStatus  # noqa: F401,E402
from app.models.analytics import DailySales  # noqa: F401,E402
