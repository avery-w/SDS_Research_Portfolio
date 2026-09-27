from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import User, Store, Product, Order, OrderItem, OrderStatus
from app.schemas import (
    StoreCreate, StoreResponse, ProductCreate, ProductUpdate,
    ProductResponse, OrderResponse
)
from app.auth import get_current_seller
from decimal import Decimal
import os
from pathlib import Path

router = APIRouter(prefix="/sellers", tags=["sellers"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Store Management
@router.post("/store", response_model=StoreResponse)
def create_store(
    store_data: StoreCreate,
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db)
):
    existing_store = db.query(Store).filter(Store.owner_id == current_user.id).first()
    if existing_store:
        raise HTTPException(status_code=400, detail="You already have a store")

    store = Store(
        owner_id=current_user.id,
        name=store_data.name,
        description=store_data.description,
        logo_url=store_data.logo_url
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    return store

@router.get("/store", response_model=StoreResponse)
def get_my_store(
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db)
):
    store = db.query(Store).filter(Store.owner_id == current_user.id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store

@router.put("/store", response_model=StoreResponse)
def update_store(
    store_data: StoreCreate,
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db)
):
    store = db.query(Store).filter(Store.owner_id == current_user.id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    store.name = store_data.name
    store.description = store_data.description
    if store_data.logo_url:
        store.logo_url = store_data.logo_url

    db.commit()
    db.refresh(store)
    return store

# Product Management
@router.post("/products", response_model=ProductResponse)
def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db)
):
    store = db.query(Store).filter(Store.owner_id == current_user.id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    sku_exists = db.query(Product).filter(Product.sku == product_data.sku).first()
    if sku_exists:
        raise HTTPException(status_code=400, detail="SKU already exists")

    product = Product(
        store_id=store.id,
        name=product_data.name,
        description=product_data.description,
        price=product_data.price,
        stock=product_data.stock,
        sku=product_data.sku,
        category=product_data.category,
        image_urls=product_data.image_urls
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

@router.get("/products", response_model=list[ProductResponse])
def list_my_products(
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db)
):
    store = db.query(Store).filter(Store.owner_id == current_user.id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    products = db.query(Product).filter(Product.store_id == store.id).all()
    return products

@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    store = db.query(Store).filter(Store.owner_id == current_user.id).first()
    if not store or product.store_id != store.id:
        raise HTTPException(status_code=403, detail="Not your product")

    if product_data.name:
        product.name = product_data.name
    if product_data.description:
        product.description = product_data.description
    if product_data.price:
        product.price = product_data.price
    if product_data.stock is not None:
        product.stock = product_data.stock
    if product_data.category:
        product.category = product_data.category
    if product_data.image_urls:
        product.image_urls = product_data.image_urls

    db.commit()
    db.refresh(product)
    return product

@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    store = db.query(Store).filter(Store.owner_id == current_user.id).first()
    if not store or product.store_id != store.id:
        raise HTTPException(status_code=403, detail="Not your product")

    product.is_active = False
    db.commit()
    return {"message": "Product deactivated"}

# Image Upload
@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_seller)
):
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        raise HTTPException(status_code=400, detail="Invalid image format")

    filename = f"{current_user.id}_{file.filename}"
    filepath = UPLOAD_DIR / filename

    with open(filepath, "wb") as f:
        f.write(await file.read())

    return {"url": f"/uploads/{filename}"}

# Orders Management
@router.get("/orders", response_model=list[OrderResponse])
def get_seller_orders(
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db)
):
    orders = db.query(Order).join(
        OrderItem, Order.id == OrderItem.order_id
    ).filter(
        OrderItem.seller_id == current_user.id
    ).distinct().all()
    return orders

@router.put("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    new_status: str,
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    is_seller_order = db.query(OrderItem).filter(
        OrderItem.order_id == order_id,
        OrderItem.seller_id == current_user.id
    ).first()

    if not is_seller_order:
        raise HTTPException(status_code=403, detail="Not your order")

    try:
        order.status = OrderStatus[new_status.upper()]
        db.commit()
        return {"message": f"Order status updated to {new_status}"}
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid status")

# Sales Analytics
@router.get("/analytics")
def get_seller_analytics(
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db)
):
    order_items = db.query(OrderItem).filter(
        OrderItem.seller_id == current_user.id
    ).all()

    total_sales = sum(item.price_at_purchase * item.quantity for item in order_items)
    total_orders = db.query(func.count(func.distinct(OrderItem.order_id))).filter(
        OrderItem.seller_id == current_user.id
    ).scalar()

    products = db.query(Product).join(
        Store, Product.store_id == Store.id
    ).filter(Store.owner_id == current_user.id).all()

    return {
        "total_sales": total_sales,
        "total_orders": total_orders,
        "total_products": len(products),
        "active_products": sum(1 for p in products if p.is_active)
    }
