
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SellerProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=3, max_length=150)

    description: str | None = Field(
        default=None,
        max_length=2000
    )

    price: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=2
    )

    stock: int = Field(ge=0)

    category_id: int | None = Field(
        default=None,
        gt=0
    )



class SellerProductUpdate(BaseModel):
    model_config=ConfigDict(extra="forbid")

    price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2
    )

    stock: int =Field(
        default=None,
        ge=0
    )

    @model_validator(mode = "after")
    def check_fields(self):
        if self.price is None and self.stock is None:
            raise ValueError("Fiyat veya stok alanlarnadan en az biri eksik")

        return self


class SellerProductVisibilityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool
