
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    field_validator,
    model_validator,
)

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

    #Ürünün uyumlu olduğu telefon modelleri
    model_ids: list[PositiveInt] = Field(
        default_factory=list,
        max_length=20,
    )

    @field_validator("model_ids")
    @classmethod
    def validate_model_ids(cls, value):
        if len(value) != len(set(value)):
            raise ValueError(
                "Aynı telefon modeli birden fazla kez seçilemez"
            )
        return value



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

    #Satıcı mevcut ürününün adını değiştirebilmeli
    name: str |None =Field(
        default=None,
        min_length=3,
        max_length=150
    )

    category_id: PositiveInt | None = None
    model_ids: list[PositiveInt] | None = Field(default=None, max_length=20)

    @field_validator("model_ids")
    @classmethod
    def unique_model_ids(cls, value):
        if value is not None and len(value) != len(set(value)):
            raise ValueError("Aynı telefon modeli birden fazla kez seçilemez")
        return value

    @model_validator(mode = "after")
    def check_fields(self):
        if (
                self.price is None
                and self.stock is None
                and self.name is None
                and self.image_url is None
                and self.category_id is None
                and self.model_ids is None):
            raise ValueError("Güncellenecek en az bir alan gerekli")

        if (self.category_id is None) != (self.model_ids is None):
            raise ValueError("Kılıf türü ve telefon modelleri birlikte gönderilmeli")

        return self


class SellerProductVisibilityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool



# SATICININ URUN KATEGORISINI VE UYUMLU TELEFON MODELLERINI BELIRLEMESI
class SellerProductCompatibilityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #Ürünün kılıf türü
    category_id: PositiveInt #Postgre sql de kimlik numaraları pozitif olmak zorunda olduğundan böyle

    # Urunun uyumlu oldugu telefon modellerinin ID listesi

    model_ids : list[PositiveInt] = Field(
        min_length=0,
        max_length=20,
    )

    #Aynı telefon modeli iki kez seçilmesin

    @field_validator("model_ids")
    @classmethod
    def validate_model_ids(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("Ayni Telefon Modeli Birden Fazla Seçilemez")
        return value
