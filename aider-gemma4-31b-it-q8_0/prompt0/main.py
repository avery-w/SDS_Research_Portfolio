import os
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import List

from models import Base, User, Store, Product, Cart, CartItem, Order, OrderItem, UserRole, OrderStatus
from auth import (
    get_password_hash, verify_password, create_access_token, 
    get_current_user, RoleChecker
)
import shipping
import chatbot
import admin_service

# Database Setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/ecommerce_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="E-Commerce API")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to get current user object
def get_user_from_db(db: Session = Depends(get_db), email: str = Depends(get_current_user)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# --- AUTH ROUTES ---

@app.post("/auth/register")
def register(email: str, password: str, role: UserRole, db: Session = Depends(get_db)):
    hashed_pw = get_password_hash(password)
    user = User(email=email, hashed_password=hashed_pw, role=role)
    db.add(user)
    db.commit()
    return {"message": "User created successfully"}

@app.post("/auth/login")
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    token = create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

# --- CUSTOMER ROUTES ---

@app.get("/products/search")
def search_products(q: str = None, category: str = None, db: Session = Depends(get_db)):
    query = db.query(Product)
    if q:
        query = query.filter(Product.name.contains(q))
    if category:
        query = query.filter(Product.category == category)
    return query.all()

@app.post("/cart/add")
def add_to_cart(product_id: int, quantity: int, user: User = Depends(get_user_from_db), db: Session = Depends(get_db)):
    cart = db.query(Cart).filter(Cart.user_id == user.id).first()
    if not cart:
        cart = Cart(user_id=user.id)
        db.add(cart)
        db.commit()
    
    item = CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity)
    db.add(item)
    db.commit()
    return {"message": "Added to cart"}

@app.post("/cart/checkout")
def checkout(shipping_address: str, destination_zip: str, weight: float, user: User = Depends(get_user_from_db), db: Session = Depends(get_db)):
    cart = db.query(Cart).filter(Cart.user_id == user.id).first()
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Calculate Shipping
    ship_cost = shipping.calculate_ups_rate(destination_zip, weight)
    
    # Calculate Total
    subtotal = sum(item.product.price * item.quantity for item in cart.items)
    total = subtotal + ship_cost
    
    order = Order(customer_id=user.id, total_price=total, shipping_address=shipping_address, status=OrderStatus.PENDING)
    db.add(order)
    db.commit()
    
    # Move items to OrderItems
    for item in cart.items:
        oi = OrderItem(order_id=order.id, product_id=item.product_id, quantity=item.quantity, unit_price=item.product.price)
        db.add(oi)
    
    # Clear Cart
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
    
    return {"order_id": order.id, "total_price": total, "shipping_cost": ship_cost}

@app.get("/orders/my-orders")
def my_orders(user: User = Depends(get_user_from_db), db: Session = Depends(get_db)):
    return db.query(Order).filter(Order.customer_id == user.id).all()

# --- SELLER ROUTES ---

@app.put("/seller/store", user: User = Depends(RoleChecker([UserRole.SELLER])), db: Session = Depends(get_db))
def update_store(name: str, description: str, user: User = Depends(get_user_from_db)):
    store = db.query(Store).filter(Store.seller_id == user.id).first()
    if not store:
        store = Store(seller_id=user.id)
        db.add(store)
    
    store.store_name = name
    store.description = description
    db.commit()
    return store

@app.post("/seller/products", user: User = Depends(RoleChecker([UserRole.SELLER])), db: Session = Depends(get_db))
def create_product(name: str, price: float, stock: int, category: str, user: User = Depends(get_user_from_db)):
    store = db.query(Store).filter(Store.seller_id == user.id).first()
    if not store:
        raise HTTPException(status_code=400, detail="Store not found. Create a store first.")
    
    product = Product(store_id=store.id, name=name, price=price, stock_quantity=stock, category=category)
    db.add(product)
    db.commit()
    return product

@app.get("/seller/orders", user: User = Depends(RoleChecker([UserRole.SELLER])), db: Session = Depends(get_db))
def seller_orders(user: User = Depends(get_user_from_db)):
    # Get orders containing products from this seller's store
    store = db.query(Store).filter(Store.seller_id == user.id).first()
    products = db.query(Product).filter(Product.store_id == store.id).all()
    product_ids = [p.id for p in products]
    
    orders = db.query(Order).join(OrderItem).filter(OrderItem.product_id.in_(product_ids)).all()
    return orders

# --- ADMIN ROUTES ---

@app.patch("/admin/users/{user_id}", user: User = Depends(RoleChecker([UserRole.ADMIN])), db: Session = Depends(get_db))
def manage_user(user_id: int, is_active: bool):
    updated_user = admin_service.toggle_user_status(db, user_id, is_active)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

@app.get("/admin/analytics", user: User = Depends(RoleChecker([UserRole.ADMIN])), db: Session = Depends(get_db))
def get_analytics():
    return admin_service.get_platform_analytics(db)

# --- AI & MESSAGING ---

@app.post("/chat")
def chat(query: str, product_id: int = None, db: Session = Depends(get_db)):
    context = None
    if product_id:
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            context = f"Product: {product.name}, Price: {product.price}, Description: {product.description}"
    
    response = chatbot.get_ai_response(query, context)
    return {"response": response}

@app.post("/messages/send")
def send_message(receiver_id: int, content: str, user: User = Depends(get_user_from_db), db: Session = Depends(get_db)):
    msg = Message(sender_id=user.id, receiver_id=receiver_id, content=content)
    db.add(msg)
    db.commit()
    return {"status": "sent"}
