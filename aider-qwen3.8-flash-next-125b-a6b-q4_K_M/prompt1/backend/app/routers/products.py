from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.database import get_db
from app.models.user import User, UserRole
from app.models.product import Product
from app.models.store import Store
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.utils.security import get_current_user, require_role
from app.utils.validators import slugify

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=list[ProductResponse])
async def list_products(
    search: str | None = None,
    category: str | None = None,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).where(Product.is_active == True)
    if search:
        query = query.where(
            or_(Product.name.ilike(f"%{search}%"), Product.description.ilike(f"%{search}%"))
        )
    if category:
        query = query.where(Product.category == category)
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.is_active == True))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    current_user: User = Depends(require_role(UserRole.SELLER)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Store).where(Store.owner_id == current_user.id))
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=400, detail="You must create a store first")

    product = Product(
        **data.model_dump(),
        slug=slugify(data.name),
        store_id=store.id,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if current_user.role == UserRole.SELLER:
        store_result = await db.execute(select(Store).where(Store.owner_id == current_user.id))
        store = store_result.scalar_one_or_none()
        if not store or product.store_id != store.id:
            raise HTTPException(status_code=403, detail="Not authorized to edit this product")
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)
    await db.flush()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if current_user.role == UserRole.SELLER:
        store_result = await db.execute(select(Store).where(Store.owner_id == current_user.id))
        store = store_result.scalar_one_or_none()
        if not store or product.store_id != store.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    product.is_active = False
    await db.flush()
