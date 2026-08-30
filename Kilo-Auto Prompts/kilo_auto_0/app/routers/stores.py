from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth import get_current_active_user, require_role
from app.database import get_session
from app.models import Store, User, UserRole
from app.schemas import StoreCreate, StoreRead

router = APIRouter(prefix="/stores", tags=["stores"])


@router.post("/", response_model=StoreRead, status_code=status.HTTP_201_CREATED)
def create_store(store: StoreCreate, current_user: User = Depends(require_role(UserRole.SELLER, UserRole.ADMIN)), session: Session = Depends(get_session)):
    db_store = Store(**store.dict(), owner_id=current_user.id)
    session.add(db_store)
    session.commit()
    session.refresh(db_store)
    return db_store


@router.get("/", response_model=list[StoreRead])
def list_stores(session: Session = Depends(get_session)):
    return session.exec(select(Store)).all()


@router.get("/{store_id}", response_model=StoreRead)
def get_store(store_id: int, session: Session = Depends(get_session)):
    store = session.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.put("/{store_id}", response_model=StoreRead)
def update_store(store_id: int, update: StoreCreate, current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)):
    store = session.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    if current_user.role != UserRole.ADMIN and store.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not permitted")
    store.name = update.name
    store.description = update.description
    session.add(store)
    session.commit()
    session.refresh(store)
    return store
