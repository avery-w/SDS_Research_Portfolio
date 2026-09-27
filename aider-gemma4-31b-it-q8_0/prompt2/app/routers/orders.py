from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import get_db
from . import models, schemas, auth
from .services.shipping import ShippingService

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/", response_model=schemas.OrderOut)
def create_order(
    order_in: schemas.OrderCreate, 
    db: Session = Depends(get_db), 
    user: models.User = Depends(auth.get_current_user)
):
    total_price = 0.0
    order_items = []
    
    for item in order_in.items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product or product.stock_quantity < item.quantity:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} unavailable or out of stock")
        
        unit_price = product.price
        total_price += unit_price * item.quantity
        
        order_items.append(models.OrderItem(product_id=item.product_id, quantity=item.quantity, unit_price=unit_price))
        product.stock_quantity -= item.quantity

    # Calculate shipping (assuming average weight of 2lbs per item for this example)
    shipping_cost = ShippingService.calculate_shipping("00000", 2.0 * len(order_in.items))
    total_price += shipping_cost

    order = models.Order(
        customer_id=user.id, 
        total_price=total_price, 
        shipping_address=order_in.shipping_address
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    for oi in order_items:
        oi.order_id = order.id
        db.add(oi)
    
    db.commit()
    return order
