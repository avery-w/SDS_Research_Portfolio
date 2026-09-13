import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import require_seller, get_current_user
from ..models import Store, Product, ProductImage, OrderItem, User, ItemStatus, ReturnRequest, ReturnStatus
from ..schemas import (
    StoreCreate, StoreOut, ProductCreate, ProductUpdate, ProductOut,
    OrderItemOut, ItemStatusUpdate, ReturnRequestOut, ReturnDecision,
)

router = APIRouter(prefix="/api/seller", tags=["seller"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _product_out(p: Product) -> ProductOut:
    out = ProductOut.model_validate(p, from_attributes=True)
    out.images = [f"/uploads/{img.filename}" for img in p.images]
    return out


def _get_own_store(db: Session, user: User) -> Store:
    store = db.query(Store).filter(Store.owner_id == user.id).first()
    if store is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You don't have a store yet, create one first")
    return store


def _get_own_product(db: Session, user: User, product_id: int) -> Product:
    store = _get_own_store(db, user)
    product = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).first()
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found in your store")
    return product


# ---- Store ----
@router.post("/store", response_model=StoreOut, status_code=status.HTTP_201_CREATED)
def create_store(payload: StoreCreate, user: User = Depends(require_seller), db: Session = Depends(get_db)):
    if db.query(Store).filter(Store.owner_id == user.id).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You already have a store")
    store = Store(owner_id=user.id, name=payload.name, description=payload.description)
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.get("/store", response_model=StoreOut)
def get_my_store(user: User = Depends(require_seller), db: Session = Depends(get_db)):
    return _get_own_store(db, user)


# ---- Products ----
@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, user: User = Depends(require_seller), db: Session = Depends(get_db)):
    store = _get_own_store(db, user)
    product = Product(store_id=store.id, **payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return _product_out(product)


@router.get("/products", response_model=list[ProductOut])
def list_my_products(user: User = Depends(require_seller), db: Session = Depends(get_db)):
    store = _get_own_store(db, user)
    products = (
        db.query(Product).options(joinedload(Product.images)).filter(Product.store_id == store.id).all()
    )
    return [_product_out(p) for p in products]


@router.patch("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, payload: ProductUpdate, user: User = Depends(require_seller), db: Session = Depends(get_db)):
    product = _get_own_product(db, user, product_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return _product_out(product)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, user: User = Depends(require_seller), db: Session = Depends(get_db)):
    product = _get_own_product(db, user, product_id)
    db.delete(product)
    db.commit()


@router.post("/products/{product_id}/images", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def upload_product_image(product_id: int, file: UploadFile = File(...), user: User = Depends(require_seller), db: Session = Depends(get_db)):
    product = _get_own_product(db, user, product_id)
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Image must be JPEG, PNG, WEBP, or GIF")

    contents = file.file.read()
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Image must be 5MB or smaller")

    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
        f.write(contents)

    db.add(ProductImage(product_id=product.id, filename=filename))
    db.commit()
    db.refresh(product)
    return _product_out(product)


# ---- Orders / fulfillment ----
@router.get("/orders", response_model=list[OrderItemOut])
def list_store_order_items(user: User = Depends(require_seller), db: Session = Depends(get_db)):
    store = _get_own_store(db, user)
    items = (
        db.query(OrderItem)
        .options(joinedload(OrderItem.product))
        .filter(OrderItem.store_id == store.id)
        .all()
    )
    return [
        OrderItemOut(
            id=i.id, product_id=i.product_id, product_name=i.product.name,
            store_id=i.store_id, quantity=i.quantity, unit_price_cents=i.unit_price_cents, status=i.status,
        )
        for i in items
    ]


@router.patch("/orders/items/{item_id}", response_model=OrderItemOut)
def update_order_item_status(item_id: int, payload: ItemStatusUpdate, user: User = Depends(require_seller), db: Session = Depends(get_db)):
    store = _get_own_store(db, user)
    item = db.query(OrderItem).options(joinedload(OrderItem.product)).filter(OrderItem.id == item_id, OrderItem.store_id == store.id).first()
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order item not found in your store")

    allowed_transitions = {
        ItemStatus.pending: {ItemStatus.fulfilled, ItemStatus.cancelled},
        ItemStatus.fulfilled: {ItemStatus.shipped, ItemStatus.cancelled},
        ItemStatus.shipped: {ItemStatus.delivered},
    }
    if payload.status not in allowed_transitions.get(item.status, set()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Cannot move item from {item.status.value} to {payload.status.value}")

    item.status = payload.status
    db.commit()
    db.refresh(item)
    return OrderItemOut(
        id=item.id, product_id=item.product_id, product_name=item.product.name,
        store_id=item.store_id, quantity=item.quantity, unit_price_cents=item.unit_price_cents, status=item.status,
    )


@router.get("/returns", response_model=list[ReturnRequestOut])
def list_store_return_requests(user: User = Depends(require_seller), db: Session = Depends(get_db)):
    store = _get_own_store(db, user)
    requests = (
        db.query(ReturnRequest)
        .join(OrderItem)
        .filter(OrderItem.store_id == store.id)
        .all()
    )
    return requests


@router.patch("/returns/{return_id}", response_model=ReturnRequestOut)
def decide_return_request(return_id: int, payload: ReturnDecision, user: User = Depends(require_seller), db: Session = Depends(get_db)):
    store = _get_own_store(db, user)
    ret = (
        db.query(ReturnRequest)
        .join(OrderItem)
        .options(joinedload(ReturnRequest.order_item))
        .filter(ReturnRequest.id == return_id, OrderItem.store_id == store.id)
        .first()
    )
    if ret is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Return request not found in your store")
    if ret.status != ReturnStatus.pending:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This return request has already been decided")

    ret.status = ReturnStatus.approved if payload.approve else ReturnStatus.denied
    if payload.approve:
        ret.order_item.status = ItemStatus.returned
    db.commit()
    db.refresh(ret)
    return ret
