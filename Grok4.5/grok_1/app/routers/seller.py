import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..auth import require_role
from ..models import User, Store, Product, Order, OrderItem, OrderStatus, UserRole
from ..schemas import ProductUpdate, ProductOut, OrderOut, StoreOut, StoreUpdate
from ..config import get_settings

router = APIRouter(prefix="/seller", tags=["seller"])
settings = get_settings()

ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


def _seller_store(user: User, db: Session) -> Store:
    store = db.query(Store).filter(Store.owner_id == user.id).first()
    if not store:
        raise HTTPException(status_code=400, detail="Seller has no store")
    if not store.is_active:
        raise HTTPException(status_code=403, detail="Your store has been deactivated")
    return store


@router.get("/store", response_model=StoreOut)
def my_store(
    current_user: User = Depends(require_role(UserRole.seller)),
    db: Session = Depends(get_db),
):
    """401/403 if not seller; 400 if no store."""
    return _seller_store(current_user, db)


@router.put("/store", response_model=StoreOut)
def update_store(
    body: StoreUpdate,
    current_user: User = Depends(require_role(UserRole.seller)),
    db: Session = Depends(get_db),
):
    """401/403 if not seller; 422 on validation errors."""
    store = _seller_store(current_user, db)
    store.name = body.name
    store.description = body.description
    db.commit()
    db.refresh(store)
    return store


@router.get("/products", response_model=list[ProductOut])
def list_my_products(
    current_user: User = Depends(require_role(UserRole.seller)),
    db: Session = Depends(get_db),
):
    store = _seller_store(current_user, db)
    return (
        db.query(Product)
        .filter(Product.store_id == store.id)
        .order_by(Product.created_at.desc())
        .all()
    )


@router.post("/products", response_model=ProductOut, status_code=201)
async def create_product(
    name: str = Form(..., min_length=1, max_length=255),
    description: str = Form(""),
    price: float = Form(..., gt=0),
    inventory: int = Form(0, ge=0),
    weight_lb: float = Form(1.0, gt=0),
    length_in: float = Form(10.0, gt=0),
    width_in: float = Form(8.0, gt=0),
    height_in: float = Form(4.0, gt=0),
    image: UploadFile | None = File(None),
    current_user: User = Depends(require_role(UserRole.seller)),
    db: Session = Depends(get_db),
):
    """
    Create product with optional image.
    - 401/403: not seller / store inactive
    - 400: bad image type or too large
    - 422: invalid form values
    """
    store = _seller_store(current_user, db)

    image_path = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1].lower()
        if ext not in ALLOWED_IMAGE_EXT:
            raise HTTPException(status_code=400, detail=f"Unsupported image type. Allowed: {ALLOWED_IMAGE_EXT}")
        content = await image.read()
        if len(content) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=400, detail="Image exceeds 5 MB limit")
        filename = f"{uuid.uuid4().hex}{ext}"
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        with open(os.path.join(settings.UPLOAD_DIR, filename), "wb") as f:
            f.write(content)
        image_path = filename

    product = Product(
        store_id=store.id,
        name=name,
        description=description,
        price=price,
        inventory=inventory,
        weight_lb=weight_lb,
        length_in=length_in,
        width_in=width_in,
        height_in=height_in,
        image_path=image_path,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    body: ProductUpdate,
    current_user: User = Depends(require_role(UserRole.seller)),
    db: Session = Depends(get_db),
):
    """401/403 not seller; 404 product not owned; 422 validation."""
    store = _seller_store(current_user, db)
    product = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    current_user: User = Depends(require_role(UserRole.seller)),
    db: Session = Depends(get_db),
):
    """Soft-delete. 401/403/404 as above."""
    store = _seller_store(current_user, db)
    product = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_active = False
    db.commit()


@router.get("/orders", response_model=list[OrderOut])
def list_my_orders(
    current_user: User = Depends(require_role(UserRole.seller)),
    db: Session = Depends(get_db),
):
    """Orders containing at least one of this seller's items. 401/403 if not seller."""
    order_ids = (
        db.query(OrderItem.order_id)
        .filter(OrderItem.seller_id == current_user.id)
        .distinct()
        .all()
    )
    ids = [r[0] for r in order_ids]
    if not ids:
        return []
    return (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .filter(Order.id.in_(ids))
        .order_by(Order.created_at.desc())
        .all()
    )


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    status: OrderStatus = Query(...),
    current_user: User = Depends(require_role(UserRole.seller)),
    db: Session = Depends(get_db),
):
    """
    Seller may advance status only for orders that contain their items.
    - 401/403: not seller
    - 404: order not found or not yours
    - 400: illegal status transition
    """
    has_item = (
        db.query(OrderItem)
        .filter(OrderItem.order_id == order_id, OrderItem.seller_id == current_user.id)
        .first()
    )
    if not has_item:
        raise HTTPException(status_code=404, detail="Order not found or does not belong to you")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    allowed = {
        OrderStatus.paid: {OrderStatus.shipped},
        OrderStatus.shipped: {OrderStatus.delivered},
        OrderStatus.return_requested: {OrderStatus.returned, OrderStatus.shipped},
    }
    if status not in allowed.get(order.status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change status from '{order.status.value}' to '{status.value}'",
        )
    order.status = status
    db.commit()
    db.refresh(order)
    return order
