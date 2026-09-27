from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User, UserRole
from app.models.store import Store
from app.schemas.store import StoreCreate, StoreUpdate, StoreResponse
from app.utils.security import get_current_user, require_role

router = APIRouter(prefix="/api/stores", tags=["stores"])


@router.get("", response_model=list[StoreResponse])
async def list_stores(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Store).where(Store.is_active == True).offset(offset).limit(per_page)
    )
    return result.scalars().all()


@router.get("/{store_id}", response_model=StoreResponse)
async def get_store(store_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Store).where(Store.id == store_id, Store.is_active == True))
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.post("", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
async def create_store(
    data: StoreCreate,
    current_user: User = Depends(require_role(UserRole.SELLER)),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Store).where(Store.owner_id == current_user.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You already have a store")
    store = Store(**data.model_dump(), owner_id=current_user.id)
    db.add(store)
    await db.flush()
    await db.refresh(store)
    return store


@router.patch("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: int,
    data: StoreUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    if store.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(store, key, value)
    await db.flush()
    await db.refresh(store)
    return store
