from fastapi import FastAPI
from app.api import auth, products, stores, shipping, ai, admin

app = FastAPI(title="Marketplace API")

# Include Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(stores.router, prefix="/api/stores", tags=["Stores"])
app.include_router(shipping.router, prefix="/api/shipping", tags=["Shipping"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI Assistant"])
app.include_router(admin.router, prefix="/api/admin", tags=["Administration"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Marketplace API. Visit /docs for OpenAPI documentation."}
