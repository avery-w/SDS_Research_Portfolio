import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from .database import get_db
from . import models, schemas, auth

router = APIRouter(prefix="/stores", tags=["Stores"])

@router.post("/", response_model=schemas.StoreOut)
def create_store(
    store_in: schemas.StoreCreate, 
    db: Session = Depends(get_db), 
    user: models.User = Depends(auth.RoleChecker([models.UserRole.seller, models.UserRole.admin]))
):
    store = models.Store(**store_in.dict(), seller_id=user.id)
    db.add(store)
    db.commit()
    db.refresh(store)
    return store

@router.post("/products", response_model=schemas.ProductOut)
async def create_product(
    product_in: schemas.ProductCreate, 
    store_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db), 
    user: models.User = Depends(auth.RoleChecker([models.UserRole.seller, models.UserRole.admin]))
):
    # Verify store ownership
    store = db.query(models.Store).filter(models.Store.id == store_id, models.Store.seller_id == user.id).first()
    if not store:
        raise HTTPException(status_code=403, detail="You do not own this store")

    # Secure file path handling
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    filename = os.path.basename(file.filename)
    file_path = os.path.join(upload_dir, filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    product = models.Product(**product_in.dict(), store_id=store_id, image_path=file_path)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product
