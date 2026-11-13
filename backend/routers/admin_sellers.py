from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from psycopg.types.json import Jsonb

from core.dependencies import require_admin
from database import get_connection

router = APIRouter(
    prefix="/api/admin/seller-application",
    tags=["admin-seller-application"],
)


#Admin Onay veya Ret Kararı

class SellerApplicationReview(BaseModel):
    decision: Literal["approved","rejected"]

    reason: str | None = Field(
        default=None,
        max_length=500,
    )

    @model_validator(mode="after")
    def validate_reason(self):
        #Reddedilen başvurularda gerekçe zorunludur

        if self.decision == "rejected":
            if not self.reason or not self.reason.strip():
                raise ValueError(
                    "Başvuru reddedilirken gerekçe belirtilmelidir."
                )

        return self

# 1. Mağaza Başvurularını Listele

@router.get("")

def list_seller_applications(
        status: Literal[
            "pending",
            "approved",
            "rejected",
        ] ="pending",
        current_admin: dict = Depends(require_admin),
):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    s.id,
                    s.store_name,
                    s.description,
                    s.approval_status,
                    s.created_at,
                    u.id,
                    u.full_name,
                    u.email
                FROM sellers AS s
                JOIN users AS u
                    ON u.id = s.owner_user_id
                WHERE s.approval_status = %s
                ORDER BY s.created_at DESC, s.id DESC
                """,
                (status,),
            )

            rows = cursor.fetchall()

    return [{
        "seller_id": row[0],
        "store_name": row[1],
        "description": row[2],
        "approval_status": row[3],
        "created_at": row[4],
        "owner_user_id": row[5],
        "owner_name": row[6],
        "owner_email": row[7],
    }
        for row in rows
    ]


# 2. Mağza başvurusunu onayla veya Reddet


@router.patch("/{seller_id}/review")
def review_seller_application(
        seller_id: int,
        data: SellerApplicationReview,
        current_admin : dict = Depends(require_admin),
):
    reason = data.reason.strip() if data.reason else None

    with get_connection() as connection:
        with connection.cursor() as cursor:
            # Magazayi ve sahibini kilitle.
            # Eszamanli iki adminin ayni basvuruyu
            # farkli kararlarla guncellemesini engeller.

            cursor.execute(
                """
                SELECT
                    s.id,
                    s.owner_user_id,
                    s.store_name,
                    s.approval_status,
                    u.role
                FROM sellers AS s
                JOIN users AS u
                    ON u.id = s.owner_user_id
                WHERE s.id = %s
                FOR UPDATE OF s, u
                """,
                (seller_id,),

            )
            application = cursor.fetchone()

            if application is None:
                raise HTTPException(
                    status_code=404,
                    detail= "Mağza başvurusu bulunamadı."
                )

            (
                application_id,
                owner_user_id,
                store_name,
                old_status,
                old_role,
            ) = application

            #Yanlizca bekleyen başvurular incelenebilir
            if old_status != "pending":
                raise HTTPException(
                    status_code=409,
                    detail= "Bu başvuru daha önceden sonuçlandırılmış",
                )

            if old_role != "customer":
                raise HTTPException(
                    status_code=409,
                    detail="başvuru sahibinin kullanıcı rolü uygun değil"
                )


            # Magazanin onay durumunu guncelle.
            cursor.execute(
                """
                UPDATE sellers
                SET
                    approval_status = %s,
                    reviewed_by = %s,
                    reviewed_at = NOW(),
                    review_reason = %s
                WHERE id = %s
                """,
                (
                    data.decision,
                    current_admin["id"],
                    reason,
                    application_id,
                ),
            )



            # Satici rolu yalnizca onay sonrasinda verilir.
            new_role = old_role

            if data.decision == "approved":
                cursor.execute(
                    """
                    UPDATE users
                    SET role = 'seller'
                    WHERE id = %s AND role = 'customer'
                    RETURNING id
                    """,
                    (owner_user_id,),
                )
                if cursor.fetchone() is None:
                    raise HTTPException(
                        status_code=409,
                        detail="Başvuru sahibinin kullanıcı rolü değişti.",
                    )

                new_role = "seller"


            #Admin işlemini denetim kaydına ekle.
            cursor.execute(
                """
                INSERT INTO admin_audit_logs(
                    actor_user_id,
                    action,
                    target_type,
                    target_id,
                    before_data,
                    after_data,
                    reason
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,

                (
                    current_admin["id"],
                    f"seller.{data.decision}",
                    "seller",
                    application_id,
                    #JSONB: POSTGRESQL de JSON verilerini optimize eder,
                    #ayrıştırılmış binary formatta depolamak için kullanılan bir veri türüdür.
                    Jsonb({
                        "approval_status": old_status,
                        "user_role": old_role,
                    }),
                    Jsonb({
                        "approval_status": data.decision,
                        "user_role": new_role,
                    }),
                    reason,
                ),

            )

    return {
        "seller_id": application_id,
        "store_name": store_name,
        "approval_status": data.decision,
        "owner_user_id": owner_user_id,
        "user_role": new_role,
        "message": "Mağza başvurusu sonuçlandırıldı."
    }
