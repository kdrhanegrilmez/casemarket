from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from core.dependencies import require_admin
from database import get_connection

router = APIRouter(prefix="/api/admin/stores", tags=["admin-stores"])


class StoreClosureUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_temporarily_closed: StrictBool
    reason: str = Field(min_length=5, max_length=500)

    @field_validator("reason")
    @classmethod
    def trim_reason(cls, value):
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Gerekçe en az 5 karakter olmalıdır.")
        return value


@router.patch("/{seller_id}/temporary-closure")
def update_store_closure(seller_id: int, data: StoreClosureUpdate, admin: dict = Depends(require_admin)):
    require_admin(admin)
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """SELECT id, approval_status, is_temporarily_closed, closure_reason
                   FROM sellers WHERE id = %s FOR UPDATE""", (seller_id,),
            )
            store = cursor.fetchone()
            if store is None:
                raise HTTPException(status_code=404, detail="Mağaza bulunamadı.")
            if store["approval_status"] != "approved":
                raise HTTPException(status_code=409, detail="Yalnızca onaylı mağazanın geçici kapanış durumu değiştirilebilir.")
            if store["is_temporarily_closed"] == data.is_temporarily_closed:
                raise HTTPException(status_code=409, detail="Mağazanın durumu zaten bu şekilde. Listeyi yenileyin.")
            reason = data.reason if data.is_temporarily_closed else None
            cursor.execute(
                """UPDATE sellers SET is_temporarily_closed = %s, closure_reason = %s,
                   closure_changed_at = NOW() WHERE id = %s""",
                (data.is_temporarily_closed, reason, seller_id),
            )
            cursor.execute(
                """INSERT INTO admin_audit_logs
                   (actor_user_id, action, target_type, target_id, before_data, after_data, reason)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (admin["id"], "seller.temporarily_closed" if data.is_temporarily_closed else "seller.reopened",
                 "seller", seller_id,
                 Jsonb({"is_temporarily_closed": store["is_temporarily_closed"], "closure_reason": store["closure_reason"]}),
                 Jsonb({"is_temporarily_closed": data.is_temporarily_closed, "closure_reason": reason}), data.reason),
            )
    return {"seller_id": seller_id, "is_temporarily_closed": data.is_temporarily_closed, "closure_reason": reason}
