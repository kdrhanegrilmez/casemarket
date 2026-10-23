
from pydantic import BaseModel, ConfigDict, Field


# Siparisteki tek bir urunun bilgileri.
class OrderItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=99)


# Siparisin tamami.
class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

 #extra="forbid" ile şunu yapıyoruz: id ve adet(quantity) haricinde bir şey gönderilirse pydantic'in
    #bu gönderilen değişkenleri reddetesini sağlıyor.

    items: list[OrderItemCreate] = Field(
        min_length=1,
        max_length=50,
    )
