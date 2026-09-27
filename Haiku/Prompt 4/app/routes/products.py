from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.auth import get_current_active_user

router = APIRouter(prefix="/products", tags=["products"])

@router.get("", response_model=list[schemas.Product])
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    store_id: int = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(models.Product).filter(models.Product.is_active == True)

    if search:
        query = query.filter(models.Product.name.ilike(f"%{search}%"))
    if store_id:
        query = query.filter(models.Product.store_id == store_id)

    products = query.offset(skip).limit(limit).all()
    return products

@router.get("/{product_id}", response_model=schemas.ProductWithReviews)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/{product_id}/reviews", response_model=schemas.Review)
def create_review(
    product_id: int,
    review: schemas.ReviewBase,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    existing_review = db.query(models.Review).filter(
        models.Review.product_id == product_id,
        models.Review.user_id == current_user.id
    ).first()
    if existing_review:
        raise HTTPException(status_code=400, detail="You already reviewed this product")

    if review.rating < 1 or review.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    db_review = models.Review(
        product_id=product_id,
        user_id=current_user.id,
        rating=review.rating,
        comment=review.comment
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

@router.get("/{product_id}/reviews", response_model=list[schemas.Review])
def get_reviews(product_id: int, db: Session = Depends(get_db)):
    reviews = db.query(models.Review).filter(models.Review.product_id == product_id).all()
    return reviews
