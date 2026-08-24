import os
import math
import shutil
import uuid
from typing import List

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from dotenv import load_dotenv

from .database import init_db, get_session
from .models import User, Product, Store, CartItem, Order, OrderItem, Message, ReturnRequest
from .utils import hash_password, verify_password, create_access_token
from .auth import get_current_user, role_required
import pgeocode

load_dotenv()
UPLOAD_DIR = os.getenv('UPLOAD_DIR', 'uploads')
ORIGIN_LAT = float(os.getenv('ORIGIN_LAT', '30.2849'))
ORIGIN_LON = float(os.getenv('ORIGIN_LON', '-97.7341'))

app = FastAPI(title="Marketplace")

# Allow CORS for local frontend in development; adjust in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors(), "body": exc.body})


@app.on_event('startup')
def on_start():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    init_db()

# Auth
@app.post('/api/auth/register')
def register(email: str = Form(...), password: str = Form(...), full_name: str = Form(None), role: str = Form('customer'), session: Session = Depends(get_session)):
    """Register a new user.

    Error cases:
    - Invalid input (missing fields): returns 422 with details.
    - Email already registered: returns 400.
    - Missing auth: not required for registration.
    """
    stmt = select(User).where(User.email == email)
    existing = session.exec(stmt).first()
    if existing:
        raise HTTPException(status_code=400, detail='Email already registered')
    user = User(email=email, hashed_password=hash_password(password), full_name=full_name, role=role)
    session.add(user)
    session.commit()
    session.refresh(user)
    # if seller create store
    if role == 'seller':
        store = Store(name=f"{full_name or email}'s Store", owner_id=user.id)
        session.add(store)
        session.commit()
    return {"id": user.id, "email": user.email, "role": user.role}

@app.post('/api/auth/token')
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    """Obtain access token.

    Error cases:
    - Incorrect credentials: returns 400.
    - Invalid input: returns 422.
    """
    stmt = select(User).where(User.email == form_data.username)
    user = session.exec(stmt).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail='Incorrect credentials')
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

# Products
@app.post('/api/products', dependencies=[Depends(role_required('seller'))])
async def create_product(title: str = Form(...), price: float = Form(...), inventory: int = Form(0), weight_kg: float = Form(0.0), description: str = Form(None), image: UploadFile = File(None), current: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Create a product for the authenticated seller.

    Error cases:
    - Missing auth: 401.
    - Unauthorized (not seller/admin): 403.
    - Invalid input: 422.
    - Seller has no store: 400.
    """
    # find seller store
    stmt = select(Store).where(Store.owner_id == current.id)
    store = session.exec(stmt).first()
    if not store:
        raise HTTPException(status_code=400, detail='Seller store not found')
    filename = None
    if image:
        ext = os.path.splitext(image.filename)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, 'wb') as buffer:
            shutil.copyfileobj(image.file, buffer)
    product = Product(store_id=store.id, title=title, price=price, inventory=inventory, weight_kg=weight_kg, description=description, image_filename=filename)
    session.add(product)
    session.commit()
    session.refresh(product)
    return product

@app.get('/api/products')
def list_products(q: str = None, session: Session = Depends(get_session)):
    """List products. Optional search query 'q'.

    Error cases:
    - Invalid query params: 422.
    """
    stmt = select(Product)
    if q:
        stmt = select(Product).where(Product.title.ilike(f"%{q}%") | Product.description.ilike(f"%{q}%"))
    return session.exec(stmt).all()

@app.get('/api/products/{product_id}')
def get_product(product_id: int, session: Session = Depends(get_session)):
    """Get product details by id.

    Error cases:
    - Invalid product_id: 422.
    - Not found: 404.
    """
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail='Product not found')
    return product

@app.get('/uploads/{filename}')
def get_image(filename: str):
    """Serve uploaded image files.

    Error cases:
    - File not found: 404.
    """
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail='File not found')
    return FileResponse(path)

# Cart
@app.post('/api/cart')
def add_to_cart(product_id: int, quantity: int = 1, current: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Add product to current user's cart.

    Error cases:
    - Missing auth: 401.
    - Invalid input (negative quantity): 422.
    - Product not found: 404.
    """
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail='Product not found')
    item = CartItem(user_id=current.id, product_id=product_id, quantity=quantity)
    session.add(item)
    session.commit()
    return {"status": "ok"}

@app.get('/api/cart')
def view_cart(current: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """View current user's cart items.

    Error cases:
    - Missing auth: 401.
    """
    stmt = select(CartItem).where(CartItem.user_id == current.id)
    items = session.exec(stmt).all()
    result = []
    for it in items:
        prod = session.get(Product, it.product_id)
        result.append({"id": it.id, "product": prod, "quantity": it.quantity})
    return result

# Checkout and shipping calculation (UPS-like estimator)
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

@app.post('/api/checkout/shipping_rates')
def shipping_rates(destination_zip: str, items: List[int], session: Session = Depends(get_session)):
    """Estimate shipping rates using a UPS-like heuristic.

    Error cases:
    - Invalid ZIP: 400.
    - Invalid input: 422.
    """
    # items: list of cartItem ids
    nomi = pgeocode.Nominatim('us')
    dest = nomi.query_postal_code(destination_zip)
    if math.isnan(dest.latitude) or math.isnan(dest.longitude):
        raise HTTPException(status_code=400, detail='Invalid destination zip')
    lat = dest.latitude
    lon = dest.longitude
    distance_km = haversine_km(ORIGIN_LAT, ORIGIN_LON, lat, lon)
    # compute weight
    total_weight = 0.0
    total_value = 0.0
    for cid in items:
        cart = session.get(CartItem, cid)
        if not cart:
            continue
        prod = session.get(Product, cart.product_id)
        total_weight += prod.weight_kg * cart.quantity
        total_value += prod.price * cart.quantity
    # UPS-like rates: base + per km + weight factor + insurance
    base = 5.00
    per_km = 0.02
    per_kg = 0.5
    insurance = 0.0
    if total_value > 200:
        insurance = total_value * 0.01
    cost = base + (per_km * distance_km) + (per_kg * total_weight) + insurance
    return {"service": "UPS-like Ground", "distance_km": round(distance_km,2), "cost": round(cost,2)}

@app.post('/api/checkout')
def checkout(destination_zip: str, shipping_service: str = "UPS-like Ground", items: List[int] = None, current: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Create an order and charge (simulated).

    Error cases:
    - Missing auth: 401.
    - No items: 400.
    - Product out of stock: 400.
    - Invalid input: 422.
    """
    if not items:
        raise HTTPException(status_code=400, detail='No items')
    # compute totals
    total = 0.0
    total_weight = 0.0
    for cid in items:
        cart = session.get(CartItem, cid)
        if not cart:
            continue
        prod = session.get(Product, cart.product_id)
        if prod.inventory < cart.quantity:
            raise HTTPException(status_code=400, detail=f'Product {prod.title} out of stock')
        total += prod.price * cart.quantity
        total_weight += prod.weight_kg * cart.quantity
    # shipping
    rates = shipping_rates(destination_zip, items, session)
    shipping_cost = rates['cost']
    order = Order(user_id=current.id, total_amount=total, shipping_amount=shipping_cost, status='processing')
    session.add(order)
    session.commit()
    session.refresh(order)
    for cid in items:
        cart = session.get(CartItem, cid)
        prod = session.get(Product, cart.product_id)
        oi = OrderItem(order_id=order.id, product_id=prod.id, quantity=cart.quantity, unit_price=prod.price)
        session.add(oi)
        # reduce inventory
        prod.inventory = prod.inventory - cart.quantity
        session.delete(cart)
    session.commit()
    return {"order_id": order.id, "total": total, "shipping": shipping_cost}

# Messaging and AI chatbot
@app.post('/api/messages')
def send_message(recipient_id: int, content: str = Form(...), product_id: int = Form(None), current: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Send a message from the authenticated user to another user/seller.

    Error cases:
    - Missing auth: 401.
    - Invalid input: 422.
    - Recipient not found: 404 (implicit when used).
    """
    msg = Message(sender_id=current.id, recipient_id=recipient_id, product_id=product_id, content=content)
    session.add(msg)
    session.commit()
    return {"status": "sent"}

@app.post('/api/chat')
def chat(query: str = Form(...)):
    """AI chat helper endpoint.

    Error cases:
    - Invalid input: 422.
    - If OpenAI configured but fails: returns fallback reply.
    """
    # Uses OpenAI if OPENAI_API_KEY present, otherwise simple rule-based reply encouraging contact
    from os import getenv
    key = getenv('OPENAI_API_KEY')
    if key:
        try:
            import openai
            openai.api_key = key
            resp = openai.ChatCompletion.create(model='gpt-4o-mini', messages=[{"role":"user","content":query}], max_tokens=150)
            text = resp['choices'][0]['message']['content']
            # nudge to message seller
            text += "\nIf you'd like, I can connect you with the seller for this product. Use the `message` action."
            return {"reply": text}
        except Exception:
            pass
    # fallback
    reply = "Hi! I can help with product details, shipping, and order issues. If you want a seller-specific answer, please message the seller directly using the messages feature."
    return {"reply": reply}

# Admin endpoints
@app.get('/api/admin/users', dependencies=[Depends(role_required('admin'))])
def list_users(session: Session = Depends(get_session)):
    """List all users (admin only).

    Error cases:
    - Missing auth: 401.
    - Unauthorized: 403.
    """
    stmt = select(User)
    return session.exec(stmt).all()

@app.post('/api/admin/deactivate', dependencies=[Depends(role_required('admin'))])
def deactivate_user(user_id: int, session: Session = Depends(get_session)):
    """Deactivate a user (admin only).

    Error cases:
    - Missing auth: 401.
    - Unauthorized: 403.
    - User not found: 404.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    user.is_active = False
    session.add(user)
    session.commit()
    return {"status": "deactivated"}

# Simple analytics: sales per store
@app.get('/api/admin/analytics/sales', dependencies=[Depends(role_required('admin'))])
def sales_analytics(session: Session = Depends(get_session)):
    """Return sales totals per store (admin only).

    Error cases:
    - Missing auth: 401.
    - Unauthorized: 403.
    """
    # Aggregate order items by store
    stmt = select(Store)
    stores = session.exec(stmt).all()
    data = []
    for s in stores:
        # sum orderitems for products in store
        total = 0.0
        for p in s.products:
            oid_stmt = select(OrderItem).where(OrderItem.product_id == p.id)
            items = session.exec(oid_stmt).all()
            for it in items:
                total += it.quantity * it.unit_price
        data.append({"store_id": s.id, "store_name": s.name, "sales_total": total})
    return data

# Returns and cancellations
@app.post('/api/orders/{order_id}/return')
def request_return(order_id: int, reason: str = Form(None), current: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Create a return request for an order belonging to the current user.

    Error cases:
    - Missing auth: 401.
    - Order not found or not owned: 404.
    """
    order = session.get(Order, order_id)
    if not order or order.user_id != current.id:
        raise HTTPException(status_code=404, detail='Order not found')
    rr = ReturnRequest(order_id=order_id, user_id=current.id, reason=reason)
    session.add(rr)
    session.commit()
    return {"status": "requested"}

@app.get('/api/orders', dependencies=[Depends(get_current_user)])
def my_orders(current: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """List orders for the authenticated user.

    Error cases:
    - Missing auth: 401.
    """
    stmt = select(Order).where(Order.user_id == current.id)
    return session.exec(stmt).all()

