from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from ..database import get_db
from ..models import Product, Store
from ..schemas import ProductOut

router = APIRouter(prefix="/api/products", tags=["products"])


def _to_out(p: Product) -> ProductOut:
    out = ProductOut.model_validate(p, from_attributes=True)
    out.images = [f"/uploads/{img.filename}" for img in p.images]
    return out


@router.get("", response_model=list[ProductOut])
def list_products(
    q: str | None = None,
    category: str | None = None,
    store_id: int | None = None,
    min_price_cents: int | None = None,
    max_price_cents: int | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    if limit < 1 or limit > 200:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "limit must be between 1 and 200")
    if offset < 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "offset must be >= 0")

    query = (
        db.query(Product)
        .options(joinedload(Product.images))
        .join(Store)
        .filter(Product.is_active.is_(True), Store.is_active.is_(True))
    )
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Product.name.ilike(like), Product.description.ilike(like)))
    if category:
        query = query.filter(Product.category == category)
    if store_id:
        query = query.filter(Product.store_id == store_id)
    if min_price_cents is not None:
        query = query.filter(Product.price_cents >= min_price_cents)
    if max_price_cents is not None:
        query = query.filter(Product.price_cents <= max_price_cents)

    products = query.order_by(Product.created_at.desc()).offset(offset).limit(limit).all()
    return [_to_out(p) for p in products]


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = (
        db.query(Product)
        .options(joinedload(Product.images))
        .filter(Product.id == product_id)
        .first()
    )
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return _to_out(product)
