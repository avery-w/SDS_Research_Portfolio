from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.auth import get_current_active_user

router = APIRouter(prefix="/addresses", tags=["addresses"])

@router.post("", response_model=schemas.Address)
def create_address(
    address: schemas.AddressCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_address = models.Address(
        user_id=current_user.id,
        street=address.street,
        city=address.city,
        state=address.state,
        zip_code=address.zip_code,
        country=address.country,
        is_default=address.is_default
    )
    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    return db_address

@router.get("", response_model=list[schemas.Address])
def get_addresses(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    addresses = db.query(models.Address).filter(models.Address.user_id == current_user.id).all()
    return addresses

@router.get("/{address_id}", response_model=schemas.Address)
def get_address(
    address_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    address = db.query(models.Address).filter(
        models.Address.id == address_id,
        models.Address.user_id == current_user.id
    ).first()
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    return address

@router.put("/{address_id}", response_model=schemas.Address)
def update_address(
    address_id: int,
    address_update: schemas.AddressCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    address = db.query(models.Address).filter(
        models.Address.id == address_id,
        models.Address.user_id == current_user.id
    ).first()
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    address.street = address_update.street
    address.city = address_update.city
    address.state = address_update.state
    address.zip_code = address_update.zip_code
    address.country = address_update.country
    address.is_default = address_update.is_default

    db.commit()
    db.refresh(address)
    return address

@router.delete("/{address_id}")
def delete_address(
    address_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    address = db.query(models.Address).filter(
        models.Address.id == address_id,
        models.Address.user_id == current_user.id
    ).first()
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    db.delete(address)
    db.commit()
    return {"message": "Address deleted"}
