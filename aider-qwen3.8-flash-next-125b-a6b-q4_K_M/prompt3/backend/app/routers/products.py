import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.database import get_db
from app.dependencies import get_current_seller, get_current_user
from app.models.user import User
from app.models.product import Product, ProductVariant
from app.schemas.product import ProductCreate, ProductResponse, ProductVariantCreate
from app.utils.pagination import PaginatedResponse
from app.config import get_settings
import boto3
import io

settings = get_settings()
s3_client = boto3.client("s3", region_name=settings.S3_REGION, aws_access_key_id=settings.AWS_ACCESS_KEY_ID, aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    search: str | None = None,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Product).where(Product.is_active == True)
    if search:
        query = query.where(or_(Product.title.ilike(f"%{search}%"), Product.description.ilike(f"%{search}%")))
    if category:
        query = query.where(Product.category == category)
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)

    count_query = select(Product.id).where(Product.is_active == True)
    total = len((await db.execute(count_query)).scalars().all())

    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    products = result.scalars().all()

    items = []
    for p in products:
        variants_result = await db.execute(select(ProductVariant).where(ProductVariant.product_id == p.id))
        variants = variants_result.scalars().all()
        items.append(ProductResponse.model_validate({**p.__dict__, "variants": variants}))

    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=(total + size - 1) // size)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    variants_result = await db.execute(select(ProductVariant).where(ProductVariant.product_id == product.id))
    variants = variants_result.scalars().all()
    return ProductResponse.model_validate({**product.__dict__, "variants": variants})


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db), seller: User = Depends(get_current_seller)):
    from app.models.store import Store
    store_result = await db.execute(select(Store).where(Store.seller_id == seller.id))
    store = store_result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=400, detail="Seller has no store")

    product = Product(
        store_id=store.id,
        title=data.title,
        slug=data.slug,
        description=data.description,
        price=data.price,
        currency=data.currency,
        sku=data.sku,
        stock_quantity=data.stock_quantity,
        category=data.category,
        tags=data.tags,
        images=data.images,
    )
    db.add(product)
    await db.flush()

    if data.variants:
        for v in data.variants:
            variant = ProductVariant(
                product_id=product.id,
                variant_name=v.variant_name,
                variant_value=v.variant_value,
                price_override=v.price_override,
                stock_quantity=v.stock_quantity,
            )
            db.add(variant)
        await db.flush()

    variants_result = await db.execute(select(ProductVariant).where(ProductVariant.product_id == product.id))
    variants = variants_result.scalars().all()
    return ProductResponse.model_validate({**product.__dict__, "variants": variants})


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: uuid.UUID, data: ProductCreate, db: AsyncSession = Depends(get_db), seller: User = Depends(get_current_seller)):
    from app.models.store import Store
    store_result = await db.execute(select(Store).where(Store.seller_id == seller.id))
    store = store_result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=400, detail="Seller has no store")

    result = await db.execute(select(Product).where(Product.id == product_id, Product.store_id == store.id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for field in ["title", "slug", "description", "price", "currency", "sku", "stock_quantity", "category", "tags", "images"]:
        val = getattr(data, field, None)
        if val is not None:
            setattr(product, field, val)
    await db.flush()

    variants_result = await db.execute(select(ProductVariant).where(ProductVariant.product_id == product.id))
    variants = variants_result.scalars().all()
    return ProductResponse.model_validate({**product.__dict__, "variants": variants})


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db), seller: User = Depends(get_current_seller)):
    from app.models.store import Store
    store_result = await db.execute(select(Store).where(Store.seller_id == seller.id))
    store = store_result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=400, detail="Seller has no store")

    result = await db.execute(select(Product).where(Product.id == product_id, Product.store_id == store.id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_active = False
    await db.flush()


@router.post("/{product_id}/images", status_code=201)
async def upload_image(product_id: uuid.UUID, file: UploadFile = File(...), db: AsyncSession = Depends(get_db), seller: User = Depends(get_current_seller)):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Invalid file type")
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    key = f"products/{product_id}/{file.filename}"
    s3_client.put_object(Bucket=settings.S3_BUCKET, Key=key, Body=content, ContentType=file.content_type)
    url = f"https://{settings.S3_BUCKET}.s3.{settings.S3_REGION}.amazonaws.com/{key}"

    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.images is None:
        product.images = []
    product.images = list(product.images) + [url]
    await db.flush()
    return {"url": url}
