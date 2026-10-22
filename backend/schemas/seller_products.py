
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
    # Ürün görselinin adresi. Görsel eklemek zorunlu değil

    image_url: str |None =Field(
        default=None,
        max_length=500,
    )



class SellerProductUpdate(BaseModel):
    model_config=ConfigDict(extra="forbid")

    price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2
    )

    stock: int | None =Field(
        default=None,
        ge=0
    )

    #mevcut ürünün adresini güncellemek için
    image_url: str | None = Field(
        default=None,
        max_length=500
    )

    @model_validator(mode = "after")
    def check_fields(self):
        if (
                self.price is None
                and self.stock is None
                and self.image_url is None):
            raise ValueError("Fiyat veya stok alanlarnadan en az biri eksik")

        return self


class SellerProductVisibilityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool
