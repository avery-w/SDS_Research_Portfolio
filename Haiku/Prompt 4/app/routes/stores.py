from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.auth import get_current_active_user, require_role

router = APIRouter(prefix="/stores", tags=["stores"])

@router.get("", response_model=list[schemas.Store])
def list_stores(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    stores = db.query(models.Store).filter(models.Store.is_active == True).offset(skip).limit(limit).all()
    return stores

@router.post("", response_model=schemas.Store)
def create_store(
    store: schemas.StoreCreate,
    current_user: models.User = Depends(require_role(models.UserRole.SELLER, models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    db_store = models.Store(
        owner_id=current_user.id,
        name=store.name,
        description=store.description
    )
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    return db_store

@router.get("/owner/{owner_id}", response_model=list[schemas.Store])
def get_owner_stores(owner_id: int, db: Session = Depends(get_db)):
    stores = db.query(models.Store).filter(models.Store.owner_id == owner_id).all()
    return stores

@router.get("/{store_id}", response_model=schemas.Store)
def get_store(store_id: int, db: Session = Depends(get_db)):
    store = db.query(models.Store).filter(models.Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store

@router.put("/{store_id}", response_model=schemas.Store)
def update_store(
    store_id: int,
    store_update: schemas.StoreCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    store = db.query(models.Store).filter(models.Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    if store.owner_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    store.name = store_update.name
    store.description = store_update.description
    db.commit()
    db.refresh(store)
    return store

@router.post("/{store_id}/products", response_model=schemas.Product)
def create_product(
    store_id: int,
    product: schemas.ProductCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    store = db.query(models.Store).filter(models.Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    if store.owner_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    existing_sku = db.query(models.Product).filter(models.Product.sku == product.sku).first()
    if existing_sku:
        raise HTTPException(status_code=400, detail="SKU already exists")

    db_product = models.Product(
        store_id=store_id,
        name=product.name,
        description=product.description,
        price=product.price,
        quantity_available=product.quantity_available,
        sku=product.sku,
        weight_oz=product.weight_oz
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.get("/{store_id}/products", response_model=list[schemas.Product])
def get_store_products(store_id: int, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    products = db.query(models.Product).filter(
        models.Product.store_id == store_id,
        models.Product.is_active == True
    ).offset(skip).limit(limit).all()
    return products

@router.put("/{store_id}/products/{product_id}", response_model=schemas.Product)
def update_product(
    store_id: int,
    product_id: int,
    product_update: schemas.ProductUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.store_id == store_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    store = db.query(models.Store).filter(models.Store.id == store_id).first()
    if store.owner_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    update_data = product_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product

@router.delete("/{store_id}/products/{product_id}")
def delete_product(
    store_id: int,
    product_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.store_id == store_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    store = db.query(models.Store).filter(models.Store.id == store_id).first()
    if store.owner_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    product.is_active = False
    db.commit()
    return {"message": "Product deleted"}
