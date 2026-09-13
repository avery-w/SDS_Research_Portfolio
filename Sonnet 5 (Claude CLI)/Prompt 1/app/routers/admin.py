from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from ..database import get_db
from ..deps import require_admin
from ..models import User, Store, Product, Order, OrderItem, PlatformSettings, Role, OrderStatus
from ..schemas import (
    UserOut, UserAdminUpdate, StoreOut, StoreAdminUpdate, ProductOut,
    OrderOut, OrderItemOut, PlatformSettingsOut, PlatformSettingsUpdate, AnalyticsOut,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _product_out(p: Product) -> ProductOut:
    out = ProductOut.model_validate(p, from_attributes=True)
    out.images = [f"/uploads/{img.filename}" for img in p.images]
    return out


def _order_out(order: Order) -> OrderOut:
    return OrderOut(
        id=order.id, status=order.status, ship_name=order.ship_name, ship_street=order.ship_street,
        ship_city=order.ship_city, ship_state=order.ship_state, ship_zip=order.ship_zip,
        shipping_service=order.shipping_service, shipping_cost_cents=order.shipping_cost_cents,
        subtotal_cents=order.subtotal_cents, total_cents=order.total_cents, created_at=order.created_at,
        items=[
            OrderItemOut(id=i.id, product_id=i.product_id, product_name=i.product.name, store_id=i.store_id,
                         quantity=i.quantity, unit_price_cents=i.unit_price_cents, status=i.status)
            for i in order.items
        ],
    )


# ---- Users ----
@router.get("/users", response_model=list[UserOut])
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserAdminUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't modify your own admin account here")
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(target, field, value)
    db.commit()
    db.refresh(target)
    return target


# ---- Stores ----
@router.get("/stores", response_model=list[StoreOut])
def list_stores(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(Store).all()


@router.patch("/stores/{store_id}", response_model=StoreOut)
def update_store(store_id: int, payload: StoreAdminUpdate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Store not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(store, field, value)
    db.commit()
    db.refresh(store)
    return store


# ---- Products ----
@router.get("/products", response_model=list[ProductOut])
def list_all_products(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    products = db.query(Product).options(joinedload(Product.images)).all()
    return [_product_out(p) for p in products]


@router.patch("/products/{product_id}/deactivate", response_model=ProductOut)
def deactivate_product(product_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    product = db.query(Product).options(joinedload(Product.images)).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    product.is_active = False
    db.commit()
    db.refresh(product)
    return _product_out(product)


# ---- Orders ----
@router.get("/orders", response_model=list[OrderOut])
def list_all_orders(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    orders = db.query(Order).options(joinedload(Order.items).joinedload(OrderItem.product)).order_by(Order.created_at.desc()).all()
    return [_order_out(o) for o in orders]


# ---- Platform settings ----
def _get_settings(db: Session) -> PlatformSettings:
    settings = db.get(PlatformSettings, 1)
    if settings is None:
        settings = PlatformSettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("/settings", response_model=PlatformSettingsOut)
def get_settings(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return _get_settings(db)


@router.patch("/settings", response_model=PlatformSettingsOut)
def update_settings(payload: PlatformSettingsUpdate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    settings = _get_settings(db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return settings


# ---- Analytics ----
@router.get("/analytics", response_model=AnalyticsOut)
def analytics(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    settings = _get_settings(db)
    total_users = db.query(func.count(User.id)).scalar()
    total_customers = db.query(func.count(User.id)).filter(User.role == Role.customer).scalar()
    total_sellers = db.query(func.count(User.id)).filter(User.role == Role.seller).scalar()
    total_stores = db.query(func.count(Store.id)).scalar()
    total_products = db.query(func.count(Product.id)).scalar()
    total_orders = db.query(func.count(Order.id)).scalar()

    revenue_orders = db.query(Order).filter(Order.status != OrderStatus.cancelled).all()
    total_revenue_cents = sum(o.total_cents for o in revenue_orders)
    commission_earned_cents = round(total_revenue_cents * settings.commission_bps / 10000)

    status_counts: dict[str, int] = {}
    for (status_val, count) in db.query(Order.status, func.count(Order.id)).group_by(Order.status).all():
        status_counts[status_val.value] = count

    top_rows = (
        db.query(Product.id, Product.name, func.sum(OrderItem.quantity).label("units_sold"))
        .join(OrderItem, OrderItem.product_id == Product.id)
        .group_by(Product.id)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
        .all()
    )
    top_products = [{"product_id": r[0], "name": r[1], "units_sold": int(r[2])} for r in top_rows]

    return AnalyticsOut(
        total_users=total_users, total_customers=total_customers, total_sellers=total_sellers,
        total_stores=total_stores, total_products=total_products, total_orders=total_orders,
        total_revenue_cents=total_revenue_cents, commission_earned_cents=commission_earned_cents,
        orders_by_status=status_counts, top_products=top_products,
    )
