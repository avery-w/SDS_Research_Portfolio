from pydantic import BaseModel, Field


class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, default=1)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1)


class CartItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    product_name: str | None = None
    product_price: float | None = None
    product_image: str | None = None

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    id: int
    user_id: int
    items: list[CartItemResponse] = []

    class Config:
        from_attributes = True
