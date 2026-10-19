
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

class SellerProducts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name:str = Field(min_length=3, max_length=100)
    description: str |None = Field(default=None, max_length=2000)
    price: Decimal = Field(gt=0,max_digits=10, decimal_places=2)
    stock: int =Field(ge=0)
    category: int | None = Field(default=None, gt=0)