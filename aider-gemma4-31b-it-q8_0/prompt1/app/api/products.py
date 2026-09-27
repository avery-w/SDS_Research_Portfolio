from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.schemas.schemas import ProductCreate, ProductOut
from app.api.deps import get_db, RoleChecker
from app.models.models import UserRole

router = APIRouter()
allow_seller_admin = RoleChecker([UserRole.SELLER, UserRole.ADMIN])

@router.get("/", response_model=List[ProductOut])
async def list_products(db: Session = Depends(get_db)):
    # return db.query(Product).all()
    return []

@router.post("/", response_model=ProductOut)
async def create_product(
    product_in: ProductCreate, 
    user=Depends(allow_seller_admin), 
    db: Session = Depends(get_db)
):
    # Implementation for creating product
    return ProductOut(id=1, store_id=1, **product_in.dict())

@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int, 
    product_in: ProductCreate, 
    user=Depends(allow_seller_admin), 
    db: Session = Depends(get_db)
):
    # Implementation for updating product
    return ProductOut(id=product_id, store_id=1, **product_in.dict())

@router.delete("/{product_id}")
async def delete_product(
    product_id: int, 
    user=Depends(allow_seller_admin), 
    db: Session = Depends(get_db)
):
    # Implementation for deleting product
    return {"detail": "Product deleted"}
