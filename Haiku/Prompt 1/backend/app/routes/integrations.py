from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Chatbot, Product, Store
from app.schemas import ChatbotQuery, ChatbotResponse, ShippingRateRequest, ShippingRateResponse
from app.auth import get_current_customer
from decimal import Decimal
import os
import json

router = APIRouter(prefix="/integrations", tags=["integrations"])

UPS_BASE_RATE = Decimal("5.00")
UPS_ZONE_RATES = {
    "ground": {"base": Decimal("5.00"), "per_mile": Decimal("0.01")},
    "express": {"base": Decimal("15.00"), "per_mile": Decimal("0.05")},
    "overnight": {"base": Decimal("25.00"), "per_mile": Decimal("0.10")}
}

ORIGIN = {"zip": "78705", "city": "Austin", "state": "TX"}

def calculate_shipping_rate(
    destination_zip: str,
    weight: float,
    service_type: str
) -> dict:
    rates = UPS_ZONE_RATES.get(service_type.lower(), UPS_ZONE_RATES["ground"])
    base_cost = rates["base"]
    per_mile_cost = rates["per_mile"]

    distance_km = hash(destination_zip) % 3000
    distance_miles = distance_km * 0.621371

    shipping_cost = base_cost + (per_mile_cost * distance_miles / 100)
    weight_surcharge = Decimal(str(weight)) * Decimal("0.5")
    total_cost = shipping_cost + weight_surcharge

    estimated_days = {
        "ground": 5,
        "express": 3,
        "overnight": 1
    }.get(service_type.lower(), 5)

    return {
        "cost": total_cost,
        "estimated_days": estimated_days,
        "carrier": "UPS"
    }

@router.post("/shipping/rates", response_model=ShippingRateResponse)
def get_shipping_rate(
    request: ShippingRateRequest,
    db: Session = Depends(get_db)
):
    rate_info = calculate_shipping_rate(
        request.destination_zip,
        request.weight,
        request.service_type
    )
    return rate_info

@router.post("/shipping/estimate")
def estimate_shipping(
    destination_zip: str,
    weight: float = 1.0,
    db: Session = Depends(get_db)
):
    estimates = {}
    for service in ["ground", "express", "overnight"]:
        rate_info = calculate_shipping_rate(destination_zip, weight, service)
        estimates[service] = rate_info
    return estimates

@router.post("/chatbot/query", response_model=ChatbotResponse)
def query_chatbot(
    query_data: ChatbotQuery,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    query_lower = query_data.query.lower()
    response = ""
    suggested_sellers = []

    if "product" in query_lower or "item" in query_lower:
        response = "I can help you find products! Would you like to browse by category or search for something specific? You can also message sellers directly about their products."
    elif "order" in query_lower or "purchase" in query_lower:
        response = "For order questions, please check your order history or contact the seller who sold you the item. They can provide detailed updates on shipping and delivery."
    elif "return" in query_lower or "refund" in query_lower:
        response = "You can request a return through your account. Most items can be returned within 30 days of purchase. Would you like help initiating a return?"
    elif "shipping" in query_lower or "delivery" in query_lower:
        response = "We offer multiple shipping options: Ground (5 days), Express (3 days), and Overnight delivery. Shipping cost depends on your location and the weight of your items."
    elif "payment" in query_lower or "checkout" in query_lower:
        response = "We accept credit cards and digital payments. Your payment is secure and processed during checkout."
    elif "help" in query_lower or "support" in query_lower:
        response = "I'm here to help! You can ask me about products, orders, shipping, returns, or payments. For specific seller questions, I can help connect you with them."
    else:
        response = "I'd be happy to help! You can ask me about products, orders, shipping, returns, or payments. What would you like to know?"

        similar_products = db.query(Product).filter(
            (Product.name.ilike(f"%{query_lower}%") |
             Product.description.ilike(f"%{query_lower}%"))
        ).limit(3).all()

        if similar_products:
            suggested_sellers = list(set(
                db.query(Store.name).filter(
                    Store.id.in_([p.store_id for p in similar_products])
                ).all()
            ))
            suggested_sellers = [s[0] for s in suggested_sellers]

    chat_interaction = Chatbot(
        user_id=current_user.id,
        query=query_data.query,
        response=response
    )
    db.add(chat_interaction)
    db.commit()

    return {
        "response": response,
        "suggested_sellers": suggested_sellers[:3] if suggested_sellers else None
    }

@router.get("/chatbot/history")
def get_chatbot_history(
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    history = db.query(Chatbot).filter(
        Chatbot.user_id == current_user.id
    ).order_by(Chatbot.created_at.desc()).limit(20).all()
    return history
