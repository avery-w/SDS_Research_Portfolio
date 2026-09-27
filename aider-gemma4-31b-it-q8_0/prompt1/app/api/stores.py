from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.schemas import StoreCreate, StoreOut
from app.api.deps import get_db, RoleChecker
from app.models.models import UserRole

router = APIRouter()
allow_seller_admin = RoleChecker([UserRole.SELLER, UserRole.ADMIN])

@router.post("/", response_model=StoreOut)
async def create_store(
    store_in: StoreCreate, 
    user=Depends(allow_seller_admin), 
    db: Session = Depends(get_db)
):
    return StoreOut(id=1, seller_id=user.id, **store_in.dict())

@router.get("/{store_id}", response_model=StoreOut)
async def get_store(store_id: int, db: Session = Depends(get_db)):
    return StoreOut(id=store_id, seller_id=1, store_name="Sample Store")
