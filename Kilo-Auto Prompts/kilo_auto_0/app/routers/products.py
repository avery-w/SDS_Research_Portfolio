from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select

from app.auth import get_current_active_user, require_role
from app.database import get_session
from app.models import Product, Store, User, UserRole
from app.schemas import ProductCreate, ProductRead

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(product: ProductCreate, current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)):
    store = session.get(Store, product.store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    if current_user.role != UserRole.ADMIN and store.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not permitted")
    db_product = Product(**product.dict())
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product


@router.get("/", response_model=list[ProductRead])
def list_products(
    q: Optional[str] = None,
    category: Optional[str] = None,
    store_id: Optional[int] = None,
    session: Session = Depends(get_session),
):
    stmt = select(Product).where(Product.is_active == True)
    if q:
        stmt = stmt.where(Product.name.contains(q) | Product.description.contains(q))
    if category:
        stmt = stmt.where(Product.category == category)
    if store_id:
        stmt = stmt.where(Product.store_id == store_id)
    return session.exec(stmt).all()


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductRead)
def update_product(product_id: int, update: ProductCreate, current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    store = session.get(Store, product.store_id)
    if current_user.role != UserRole.ADMIN and store.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not permitted")
    product.name = update.name
    product.description = update.description
    product.price = update.price
    product.stock = update.stock
    product.category = update.category
    product.image_url = update.image_url
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    store = session.get(Store, product.store_id)
    if current_user.role != UserRole.ADMIN and store.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not permitted")
    product.is_active = False
    session.add(product)
    session.commit()
