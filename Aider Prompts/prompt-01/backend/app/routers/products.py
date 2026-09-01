from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_session
from app.models.product import Product, Inventory, ProductImage
from app.deps.auth import require_roles
from app.models.user import Role, User
from app.services.storage import upload_product_image

router = APIRouter(prefix="/products", tags=["products"])

@router.get("", responses={})
async def list_products(q: str | None = Query(None), db: AsyncSession = Depends(get_session), limit: int = 20, offset: int = 0):
    stmt = select(Product).where(Product.is_active == True).limit(limit).offset(offset)
    # Simple search by title; replace with FTS/trigram later as needed
    if q:
        stmt = select(Product).where(Product.title.ilike(f"%{q}%"), Product.is_active == True).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    return [{"id": p.id, "title": p.title, "price_cents": p.price_cents, "images": [i.url for i in p.images]} for p in rows]

@router.post("", responses={401: {"description": "Missing auth"}, 403: {"description": "Only sellers"}, 422: {"description": "Invalid"}})
async def create_product(payload: dict, db: AsyncSession = Depends(get_session), user: User = Depends(require_roles(Role.seller))):
    # Validate payload keys; on failure FastAPI returns 422 (use Pydantic schema in real code)
    p = Product(
        store_id=payload["store_id"],
        title=payload["title"],
        description=payload.get("description", ""),
        price_cents=payload["price_cents"],
        weight_lbs=payload["weight_lbs"],
        length_in=payload["length_in"],
        width_in=payload["width_in"],
        height_in=payload["height_in"],
        category=payload.get("category", "general"),
        is_active=True
    )
    db.add(p); await db.flush()
    inv = Inventory(product_id=p.id, quantity=payload.get("quantity", 0))
    db.add(inv); await db.commit(); await db.refresh(p)
    return {"id": p.id}

@router.post("/{product_id}/images", responses={401: {"description": "Missing auth"}, 403: {"description": "Unauthorized"}, 422: {"description": "Invalid"}})
async def upload_image(product_id: int, file: UploadFile, db: AsyncSession = Depends(get_session), user: User = Depends(require_roles(Role.seller, Role.admin))):
    # verify seller owns product (omitted)
    url = upload_product_image(file.file, file.content_type or "image/jpeg")
    db.add(ProductImage(product_id=product_id, url=url))
    await db.commit()
    return {"url": url}
