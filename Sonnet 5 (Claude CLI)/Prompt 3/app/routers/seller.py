from fastapi import APIRouter, Depends, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_seller, verify_csrf
from app.models import OrderItem, Product, ProductImage, SellerMessage, Store, User
from app.utils.uploads import save_product_image

router = APIRouter(prefix="/seller")
templates = Jinja2Templates(directory="templates")


def _get_or_404_store(user: User, db: Session) -> Store | None:
    return db.scalar(select(Store).where(Store.owner_id == user.id))


@router.get("/dashboard")
def dashboard(request: Request, user: User = Depends(require_seller), db: Session = Depends(get_db)):
    store = _get_or_404_store(user, db)
    return templates.TemplateResponse(request, "seller_dashboard.html", {"user": user, "store": store})


@router.post("/store", dependencies=[Depends(verify_csrf)])
def save_store(
    name: str = Form(...),
    description: str = Form(""),
    user: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    store = _get_or_404_store(user, db)
    if store:
        store.name, store.description = name.strip(), description.strip()
    else:
        db.add(Store(owner_id=user.id, name=name.strip(), description=description.strip()))
    db.commit()
    return RedirectResponse("/seller/dashboard", status_code=303)


@router.get("/products/new")
def new_product_form(request: Request, user: User = Depends(require_seller)):
    return templates.TemplateResponse(request, "seller_product_form.html", {"user": user, "product": None})


@router.post("/products/new", dependencies=[Depends(verify_csrf)])
def create_product(
    name: str = Form(...),
    description: str = Form(""),
    price_dollars: float = Form(...),
    inventory_count: int = Form(0),
    weight_oz: float = Form(16.0),
    length_in: float = Form(10.0),
    width_in: float = Form(6.0),
    height_in: float = Form(4.0),
    user: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    store = _get_or_404_store(user, db)
    if not store:
        return RedirectResponse("/seller/dashboard", status_code=303)
    product = Product(
        store_id=store.id,
        name=name.strip(),
        description=description.strip(),
        price_cents=max(round(price_dollars * 100), 0),
        inventory_count=max(inventory_count, 0),
        weight_oz=max(weight_oz, 0.1),
        length_in=max(length_in, 0.1),
        width_in=max(width_in, 0.1),
        height_in=max(height_in, 0.1),
    )
    db.add(product)
    db.commit()
    return RedirectResponse("/seller/products", status_code=303)


@router.get("/products")
def list_products(request: Request, user: User = Depends(require_seller), db: Session = Depends(get_db)):
    store = _get_or_404_store(user, db)
    products = store.products if store else []
    return templates.TemplateResponse(request, "seller_products.html", {"user": user, "products": products})


@router.get("/products/{product_id}/edit")
def edit_product_form(product_id: int, request: Request, user: User = Depends(require_seller), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product or product.store.owner_id != user.id:
        return templates.TemplateResponse(request, "not_found.html", {"user": user}, status_code=404)
    return templates.TemplateResponse(request, "seller_product_form.html", {"user": user, "product": product})


@router.post("/products/{product_id}/edit", dependencies=[Depends(verify_csrf)])
def update_product(
    product_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    price_dollars: float = Form(...),
    inventory_count: int = Form(0),
    weight_oz: float = Form(16.0),
    length_in: float = Form(10.0),
    width_in: float = Form(6.0),
    height_in: float = Form(4.0),
    is_active: bool = Form(False),
    user: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if not product or product.store.owner_id != user.id:
        return templates.TemplateResponse(request, "not_found.html", {"user": user}, status_code=404)
    product.name = name.strip()
    product.description = description.strip()
    product.price_cents = max(round(price_dollars * 100), 0)
    product.inventory_count = max(inventory_count, 0)
    product.weight_oz = max(weight_oz, 0.1)
    product.length_in = max(length_in, 0.1)
    product.width_in = max(width_in, 0.1)
    product.height_in = max(height_in, 0.1)
    product.is_active = is_active
    db.commit()
    return RedirectResponse("/seller/products", status_code=303)


@router.post("/products/{product_id}/images", dependencies=[Depends(verify_csrf)])
def upload_image(
    product_id: int,
    image: UploadFile,
    user: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if not product or product.store.owner_id != user.id:
        return RedirectResponse("/seller/products", status_code=303)
    path = save_product_image(image)
    db.add(ProductImage(product_id=product.id, file_path=path))
    db.commit()
    return RedirectResponse(f"/seller/products/{product_id}/edit", status_code=303)


@router.get("/orders")
def seller_orders(request: Request, user: User = Depends(require_seller), db: Session = Depends(get_db)):
    store = _get_or_404_store(user, db)
    items = (
        db.scalars(
            select(OrderItem).where(OrderItem.store_id == store.id).order_by(OrderItem.id.desc())
        ).all()
        if store
        else []
    )
    return templates.TemplateResponse(request, "seller_orders.html", {"user": user, "items": items})


@router.post("/orders/{item_id}/fulfill", dependencies=[Depends(verify_csrf)])
def fulfill_item(item_id: int, user: User = Depends(require_seller), db: Session = Depends(get_db)):
    item = db.get(OrderItem, item_id)
    if item and item.store.owner_id == user.id:
        item.fulfilled = True
        db.commit()
    return RedirectResponse("/seller/orders", status_code=303)


@router.get("/messages")
def seller_message_list(request: Request, user: User = Depends(require_seller), db: Session = Depends(get_db)):
    store = _get_or_404_store(user, db)
    threads = []
    if store:
        customer_ids = db.scalars(
            select(SellerMessage.customer_id).where(SellerMessage.store_id == store.id).distinct()
        ).all()
        threads = customer_ids
    return templates.TemplateResponse(request, "seller_messages.html", {"user": user, "threads": threads, "store": store})


@router.get("/messages/{customer_id}")
def seller_message_thread(customer_id: int, request: Request, user: User = Depends(require_seller), db: Session = Depends(get_db)):
    store = _get_or_404_store(user, db)
    messages = db.scalars(
        select(SellerMessage)
        .where(SellerMessage.store_id == store.id, SellerMessage.customer_id == customer_id)
        .order_by(SellerMessage.created_at)
    ).all()
    return templates.TemplateResponse(
        request, "seller_message_thread.html", {"user": user, "messages": messages, "customer_id": customer_id}
    )


@router.post("/messages/{customer_id}", dependencies=[Depends(verify_csrf)])
def seller_reply(
    customer_id: int,
    content: str = Form(...),
    user: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    store = _get_or_404_store(user, db)
    content = content.strip()[:4000]
    if store and content:
        db.add(SellerMessage(store_id=store.id, customer_id=customer_id, sender_role="seller", content=content))
        db.commit()
    return RedirectResponse(f"/seller/messages/{customer_id}", status_code=303)
