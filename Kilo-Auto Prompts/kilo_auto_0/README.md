# kilo_auto_0
Modern e-commerce marketplace built with FastAPI + SQLModel.

## Setup
1. pip install -r requirements.txt
2. Copy .env.example to .env and fill values
3. uvicorn main:app --reload
4. Docs at http://localhost:8000/docs

## Roles
- customer: browse, cart, checkout, orders, returns, chat
- seller: store, products, inventory, fulfill orders, messages
- admin: manage users/stores/products/orders/settings, analytics, overrides

## UPS Shipping
Origin: 110 Inner Campus Drive, Austin, TX 78705

## AI Chatbot
POST /chatbot encourages direct seller messaging for product/order questions.
