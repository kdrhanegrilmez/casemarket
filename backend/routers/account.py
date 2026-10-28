from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from psycopg.errors import UniqueViolation

from core.dependencies import get_current_user
from database import get_connection

router = APIRouter(prefix="/api/account", tags=["account"])


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr


class AddressCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=2, max_length=60)
    recipient: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=30)
    city: str = Field(min_length=2, max_length=80)
    district: str = Field(min_length=2, max_length=80)
    address_line: str = Field(min_length=10, max_length=500)
    postal_code: str | None = Field(default=None, max_length=12)


class PaymentMethodCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=2, max_length=60)
    brand: str = Field(min_length=2, max_length=30)
    last_four: str = Field(pattern=r"^[0-9]{4}$")
    expiry_month: int = Field(ge=1, le=12)
    expiry_year: int = Field(ge=2026, le=2100)


@router.patch("/profile")
def update_profile(data: ProfileUpdate, user: dict = Depends(get_current_user)):
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE users SET full_name = %s, email = %s WHERE id = %s
                    RETURNING id, full_name, email, role""",
                    (data.full_name.strip(), str(data.email).lower(), user["id"]),
                )
                row = cursor.fetchone()
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="Bu e-posta adresi kullanılıyor.") from None
    return dict(zip(("id", "full_name", "email", "role"), row))


@router.get("/addresses")
def list_addresses(user: dict = Depends(get_current_user)):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, label, recipient, phone, city, district, address_line, postal_code
                FROM user_addresses WHERE user_id = %s ORDER BY id DESC""",
                (user["id"],),
            )
            rows = cursor.fetchall()
    keys = ("id", "label", "recipient", "phone", "city", "district", "address_line", "postal_code")
    return [dict(zip(keys, row)) for row in rows]


@router.post("/addresses", status_code=201)
def add_address(data: AddressCreate, user: dict = Depends(get_current_user)):
    values = (data.label.strip(), data.recipient.strip(), data.phone.strip(),
              data.city.strip(), data.district.strip(), data.address_line.strip(),
              data.postal_code, user["id"])
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO user_addresses
                (label, recipient, phone, city, district, address_line, postal_code, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                values,
            )
            address_id = cursor.fetchone()[0]
    return {"id": address_id, **data.model_dump()}


@router.delete("/addresses/{address_id}", status_code=204)
def delete_address(address_id: int, user: dict = Depends(get_current_user)):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM user_addresses WHERE id = %s AND user_id = %s RETURNING id",
                (address_id, user["id"]),
            )
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="Adres bulunamadı.")


@router.get("/payment-methods")
def list_payment_methods(user: dict = Depends(get_current_user)):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, label, brand, last_four, expiry_month, expiry_year
                FROM user_payment_methods WHERE user_id = %s ORDER BY id DESC""",
                (user["id"],),
            )
            rows = cursor.fetchall()
    keys = ("id", "label", "brand", "last_four", "expiry_month", "expiry_year")
    return [dict(zip(keys, row)) for row in rows]


@router.post("/payment-methods", status_code=201)
def add_payment_method(data: PaymentMethodCreate, user: dict = Depends(get_current_user)):
    today = date.today()
    if (data.expiry_year, data.expiry_month) < (today.year, today.month):
        raise HTTPException(status_code=422, detail="Son kullanma tarihi geçmiş bir demo kart eklenemez.")
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO user_payment_methods
                (user_id, label, brand, last_four, expiry_month, expiry_year)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (user["id"], data.label.strip(), data.brand.strip(),
                 data.last_four, data.expiry_month, data.expiry_year),
            )
            method_id = cursor.fetchone()[0]
    return {"id": method_id, **data.model_dump()}


@router.delete("/payment-methods/{method_id}", status_code=204)
def delete_payment_method(method_id: int, user: dict = Depends(get_current_user)):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM user_payment_methods WHERE id = %s AND user_id = %s RETURNING id",
                (method_id, user["id"]),
            )
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="Ödeme yöntemi bulunamadı.")
