from decimal import Decimal

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    stock: int = Field(ge=0)
    seller_id: int = Field(gt=0)


class ProductStockUpdate(BaseModel):
    stock: int = Field(ge=0)
