from sqlalchemy.orm import Session
from sqlalchemy import func
from models import User, Order, OrderItem

def toggle_user_status(db: Session, user_id: int, status: bool):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    user.is_active = status
    db.commit()
    return user

def override_order_status(db: Session, order_id: int, new_status):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None
    order.status = new_status
    db.commit()
    return order

def get_platform_analytics(db: Session):
    # Total Revenue
    total_revenue = db.query(func.sum(Order.total_price)).scalar() or 0.0
    
    # Top Selling Products
    top_products = (
        db.query(OrderItem.product_id, func.sum(OrderItem.quantity).label("total_sold"))
        .group_by(OrderItem.product_id)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
        .all()
    )
    
    # Monthly Growth (Simplified: Total orders this month vs last month)
    # In a real app, we would use date truncation and group by month
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    
    return {
        "total_platform_revenue": total_revenue,
        "top_selling_products": [{"product_id": p[0], "sold": p[1]} for p in top_products],
        "total_orders_count": total_orders
    }
