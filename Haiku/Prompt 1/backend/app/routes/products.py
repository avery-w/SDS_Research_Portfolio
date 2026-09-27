from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.database import get_db
from app.models import Product, Review
from app.schemas import ProductResponse, ReviewResponse, ReviewCreate
from decimal import Decimal

router = APIRouter(prefix="/products", tags=["products"])

@router.get("", response_model=list[ProductResponse])
def list_products(
    category: str = None,
    min_price: Decimal = None,
    max_price: Decimal = None,
    search: str = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.is_active == True)

    if search:
        query = query.filter(
            Product.name.ilike(f"%{search}%") |
            Product.description.ilike(f"%{search}%")
        )

    if category:
        query = query.filter(Product.category == category)

    if min_price is not None:
        query = query.filter(Product.price >= min_price)

    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    products = query.offset(skip).limit(limit).all()
    return products

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.get("/{product_id}/reviews", response_model=list[ReviewResponse])
def get_product_reviews(product_id: int, db: Session = Depends(get_db)):
    reviews = db.query(Review).filter(Review.product_id == product_id).all()
    return reviews

@router.post("/{product_id}/reviews", response_model=ReviewResponse)
def create_review(
    product_id: int,
    review_data: ReviewCreate,
    current_user = Depends(lambda: None),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not current_user:
        raise HTTPException(status_code=401, detail="Must be logged in to review")

    review = Review(
        product_id=product_id,
        customer_id=current_user.id,
        rating=review_data.rating,
        comment=review_data.comment
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review

@router.get("/categories/all")
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Product.category).distinct().filter(Product.is_active == True).all()
    return [cat[0] for cat in categories if cat[0]]
