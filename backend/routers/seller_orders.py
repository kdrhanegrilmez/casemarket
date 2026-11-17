from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.dependencies import get_current_user
from database import get_connection


router = APIRouter(prefix="/api/sellers/me/orders", tags=["seller-orders"])
NEXT_STATUS = {"pending": "preparing", "preparing": "shipped", "shipped": "delivered"}


class ShippingStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["preparing", "shipped", "delivered"]
    shipping_company: str | None = Field(default=None, max_length=100)
    tracking_number: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def require_tracking_when_shipped(self):
        if self.status == "shipped" and not (self.shipping_company and self.shipping_company.strip() and self.tracking_number and self.tracking_number.strip()):
            raise ValueError("Kargo firması ve takip numarası zorunludur.")
        return self


def _require_seller(user):
    if user["role"] != "seller":
        raise HTTPException(status_code=403, detail="Bu işlem için satıcı hesabı gerekli.")


@router.get("")
def get_seller_orders(current_user: dict = Depends(get_current_user)):
    _require_seller(current_user)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT o.id, o.status, o.created_at, o.shipping_address,
                       oi.id, oi.product_id, oi.product_name, oi.quantity,
                       oi.unit_price, oi.shipping_status, oi.shipping_company, oi.tracking_number
                FROM order_items AS oi
                JOIN orders AS o ON o.id = oi.order_id
                JOIN sellers AS s ON s.id = oi.seller_id
                WHERE s.owner_user_id = %s
                ORDER BY o.created_at DESC, o.id DESC, oi.id
                """,
                (current_user["id"],),
            )
            rows = cursor.fetchall()

    orders_by_id = {}
    for row in rows:
        order = orders_by_id.setdefault(row[0], {
            "id": row[0],
            "status": row[1],
            "created_at": row[2].isoformat(),
            "shipping_address": row[3],
            "seller_total": Decimal("0.00"),
            "items": [],
        })
        order["seller_total"] += row[8] * row[7]
        order["items"].append({
            "id": row[4],
            "product_id": row[5],
            "product_name": row[6],
            "quantity": row[7],
            "unit_price": str(row[8]),
            "shipping_status": row[9],
            "shipping_company": row[10],
            "tracking_number": row[11],
        })

    for order in orders_by_id.values():
        order["seller_total"] = str(order["seller_total"])
    return list(orders_by_id.values())


@router.patch("/{order_id}/items/{item_id}/shipping")
def update_shipping_status(
    order_id: int,
    item_id: int,
    data: ShippingStatusUpdate,
    current_user: dict = Depends(get_current_user),
):
    _require_seller(current_user)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT oi.shipping_status, o.status, o.shipping_address
                FROM order_items AS oi
                JOIN orders AS o ON o.id = oi.order_id
                JOIN sellers AS s ON s.id = oi.seller_id
                WHERE oi.id = %s AND o.id = %s AND s.owner_user_id = %s
                FOR UPDATE OF oi
                """,
                (item_id, order_id, current_user["id"]),
            )
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Sipariş kalemi bulunamadı.")
            current_status, order_status, address = row
            if order_status != "paid":
                raise HTTPException(status_code=409, detail="Yalnızca ödenmiş sipariş hazırlanabilir.")
            if data.status != current_status:
                if NEXT_STATUS.get(current_status) != data.status:
                    raise HTTPException(status_code=409, detail="Kargo durumu sırayla güncellenmeli.")
                if data.status == "shipped" and not address:
                    raise HTTPException(status_code=409, detail="Teslimat adresi olmayan sipariş kargoya verilemez.")
                cursor.execute(
                    """UPDATE order_items
                       SET shipping_status = %s,
                           shipping_company = COALESCE(%s, shipping_company),
                           tracking_number = COALESCE(%s, tracking_number)
                       WHERE id = %s""",
                    (data.status, data.shipping_company.strip() if data.shipping_company else None,
                     data.tracking_number.strip() if data.tracking_number else None, item_id),
                )

    return {"order_id": order_id, "item_id": item_id, "shipping_status": data.status,
            "shipping_company": data.shipping_company, "tracking_number": data.tracking_number}
