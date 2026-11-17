from fastapi import APIRouter, Depends, HTTPException
from psycopg.errors import UniqueViolation

from core.dependencies import get_current_user
from database import get_connection
from schemas.sellers import SellerCreate


router = APIRouter(prefix="/api/sellers", tags=["sellers"])


@router.post("", status_code=201)
def create_seller(
    data: SellerCreate,
    current_user: dict = Depends(get_current_user),
):
    # Yalnizca musteriler yeni magaza acabilir.
    if current_user["role"] != "customer":
        raise HTTPException(
            status_code=409,
            detail="Bu hesap yeni bir magaza acamaz.",
        )

    store_name = data.store_name.strip()

    if len(store_name) < 3:
        raise HTTPException(
            status_code=422,
            detail="Magaza adi en az 3 karakter olmali.",
        )

    description = (
        data.description.strip()
        if data.description is not None
        else None
    )

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                # Basvuru incelenene kadar kullanici musteri olarak kalir.
                cursor.execute(
                    """
                    SELECT role FROM users WHERE id = %s FOR UPDATE
                    """,
                    (current_user["id"],),
                )

                role_row = cursor.fetchone()

                if role_row is None or role_row[0] != "customer":
                    raise HTTPException(
                        status_code=409,
                        detail="Bu hesap yeni bir magaza acamaz.",
                    )

                # Magazayi giris yapan kullaniciya bagla.
                cursor.execute(
                    """
                    INSERT INTO sellers
                        (owner_user_id, store_name, description, approval_status)
                    VALUES (%s, %s, %s, 'pending')
                    ON CONFLICT (owner_user_id) DO UPDATE
                    SET store_name = EXCLUDED.store_name,
                        description = EXCLUDED.description,
                        approval_status = 'pending',
                        reviewed_by = NULL,
                        reviewed_at = NULL,
                        review_reason = NULL
                    WHERE sellers.approval_status = 'rejected'
                    RETURNING id, store_name, description, approval_status
                    """,
                    (
                        current_user["id"],
                        store_name,
                        description,
                    ),
                )

                seller = cursor.fetchone()
                if seller is None:
                    raise HTTPException(
                        status_code=409,
                        detail="Zaten bekleyen veya onaylanmış bir mağaza başvurunuz var.",
                    )

    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Bu kullaniciya ait magaza zaten var.",
        ) from None

    return {
        "id": seller[0],
        "owner_user_id": current_user["id"],
        "store_name": seller[1],
        "description": seller[2],
        "approval_status": seller[3],
    }


@router.get("/me")
def get_my_store(
    current_user: dict = Depends(get_current_user),
):
    # Sadece satıcı rolündeki kullanıcılara erişmeliyiz
    if current_user["role"] != "seller":
        raise HTTPException(
            status_code=403,
            detail="Bu işlem için satıcı hesabı gerekir.",
        )

    # Mağzaya giriş yapan kullanıcıya göre bulma:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, owner_user_id, store_name, description, is_temporarily_closed, closure_reason
                FROM sellers
                WHERE owner_user_id = %s
                """,
                (current_user["id"],),
            )

            store = cursor.fetchone()

    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Mağza bulunamadı",
        )

    return {
        "id": store[0],
        "owner_user_id": store[1],
        "store_name": store[2],
        "description": store[3],
        "is_temporarily_closed": store[4],
        "closure_reason": store[5],
    }


@router.get("/my-application")
def get_my_application(current_user: dict = Depends(get_current_user)):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, store_name, description, approval_status, created_at,
                       reviewed_at, review_reason
                FROM sellers WHERE owner_user_id = %s
                """,
                (current_user["id"],),
            )
            row = cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0], "store_name": row[1], "description": row[2],
        "approval_status": row[3], "created_at": row[4],
        "reviewed_at": row[5], "review_reason": row[6],
    }


@router.get("/me/notifications")
def get_my_notifications(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "seller":
        raise HTTPException(status_code=403, detail="Bu işlem için satıcı hesabı gerekir.")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT n.id, n.product_id, p.name, n.reason,
                       a.full_name, n.created_at, n.read_at
                FROM seller_notifications AS n
                JOIN products AS p ON p.id = n.product_id
                JOIN users AS a ON a.id = n.actor_user_id
                WHERE n.recipient_user_id = %s
                  AND n.kind = 'product_removed_by_admin'
                ORDER BY n.created_at DESC, n.id DESC
                LIMIT 50
                """,
                (current_user["id"],),
            )
            rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "product_id": row[1],
            "product_name": row[2],
            "reason": row[3],
            "admin_name": row[4],
            "created_at": row[5],
            "read_at": row[6],
        }
        for row in rows
    ]


@router.patch("/me/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] != "seller":
        raise HTTPException(status_code=403, detail="Bu işlem için satıcı hesabı gerekir.")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE seller_notifications
                SET read_at = COALESCE(read_at, NOW())
                WHERE id = %s AND recipient_user_id = %s
                RETURNING id, read_at
                """,
                (notification_id, current_user["id"]),
            )
            notification = cursor.fetchone()

    if notification is None:
        raise HTTPException(status_code=404, detail="Bildirim bulunamadı.")
    return {"id": notification[0], "read_at": notification[1]}
