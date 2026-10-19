from pydantic import BaseModel, ConfigDict, Field

class SellerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    store_name: str = Field(min_length=3, max_length=120)
    description: str | None =Field(default=None, max_length=1000)