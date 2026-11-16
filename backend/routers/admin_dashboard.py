from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from core.dependencies import require_admin
from database import get_connection


router = APIRouter(
    prefix="/api/admin",
    tags=["admin-dashboard"],
    dependencies=[Depends(require_admin)],
)

PageSize = Annotated[int, Query(ge=1, le=100)]
PageOffset = Annotated[int, Query(ge=0)]


class CommissionRateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commission_rate_percent: Decimal = Field(
        ge=0, le=100, max_digits=5, decimal_places=2,
    )


class ProductRemoval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=5, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        reason = value.strip()
        if len(reason) < 5:
            raise ValueError("Yayından kaldırma gerekçesi en az 5 karakter olmalı.")
        return reason


class ProductRestore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=5, max_length=500)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        message = value.strip()
        if len(message) < 5:
            raise ValueError("Satıcıya gönderilecek mesaj en az 5 karakter olmalı.")
        return message


def read_page(query, parameters, limit, offset):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (*parameters, limit + 1, offset))
            rows = cursor.fetchall()

    return {"items": rows[:limit], "has_more": len(rows) > limit}


@router.get("/overview")
def get_overview():
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM users WHERE role = 'customer') AS customers,
                    (SELECT COUNT(*) FROM users WHERE role = 'seller') AS sellers,
                    (SELECT COUNT(*) FROM sellers WHERE approval_status = 'approved')
                        AS approved_stores,
                    (SELECT COUNT(*) FROM sellers WHERE approval_status = 'pending')
                        AS pending_stores,
                    (SELECT COUNT(*) FROM products) AS products,
                    COUNT(*) AS paid_orders,
                    COALESCE(SUM(total_amount), 0)::text AS gross_sales
                FROM orders
                WHERE status = 'paid'
                """
            )
            overview = cursor.fetchone()
            cursor.execute(
                """
                SELECT o.id, u.full_name AS customer_name,
                       o.total_amount::text AS total_amount, o.created_at
                FROM orders AS o
                JOIN users AS u ON u.id = o.customer_id
                WHERE o.status = 'paid'
                ORDER BY o.created_at DESC, o.id DESC
                LIMIT 5
                """
            )
            overview["recent_orders"] = cursor.fetchall()
            cursor.execute(
                """
                SELECT days.day::date AS day, COUNT(o.id) AS orders
                FROM generate_series(
                    (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/Istanbul')::date - 6,
                    (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/Istanbul')::date,
                    INTERVAL '1 day'
                ) AS days(day)
                LEFT JOIN orders AS o
                    ON o.status = 'paid'
                    AND (o.created_at AT TIME ZONE 'Europe/Istanbul')::date = days.day
                GROUP BY days.day
                ORDER BY days.day
                """
            )
            overview["daily_orders"] = cursor.fetchall()
            return overview


@router.get("/users")
def list_users(
    role: Literal["customer", "seller", "admin"] | None = None,
    limit: PageSize = 25,
    offset: PageOffset = 0,
):
    return read_page(
        """
        SELECT id, full_name, email, role, created_at
        FROM users
        WHERE %s::text IS NULL OR role = %s
        ORDER BY id DESC
        LIMIT %s OFFSET %s
        """,
        (role, role), limit, offset,
    )


@router.get("/stores")
def list_stores(limit: PageSize = 25, offset: PageOffset = 0):
    return read_page(
        """
        SELECT s.id, s.store_name, s.approval_status,
               s.commission_rate_percent::text AS commission_rate_percent,
               u.full_name AS owner_name, u.email AS owner_email,
               (SELECT COUNT(*) FROM products WHERE seller_id = s.id) AS product_count
        FROM sellers AS s
        JOIN users AS u ON u.id = s.owner_user_id
        ORDER BY s.id DESC
        LIMIT %s OFFSET %s
        """,
        (), limit, offset,
    )


@router.patch("/stores/{seller_id}/commission")
def update_store_commission(
    seller_id: int,
    data: CommissionRateUpdate,
    current_admin: dict = Depends(require_admin),
):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, approval_status, commission_rate_percent
                FROM sellers
                WHERE id = %s
                FOR UPDATE
                """,
                (seller_id,),
            )
            store = cursor.fetchone()
            if store is None:
                raise HTTPException(status_code=404, detail="Mağaza bulunamadı.")
            if store["approval_status"] != "approved":
                raise HTTPException(
                    status_code=409,
                    detail="Komisyon oranı yalnızca onaylı mağazalarda ayarlanabilir.",
                )

            old_rate = store["commission_rate_percent"]
            new_rate = data.commission_rate_percent
            if old_rate == new_rate:
                return {
                    "seller_id": seller_id,
                    "commission_rate_percent": str(new_rate),
                }

            cursor.execute(
                "UPDATE sellers SET commission_rate_percent = %s WHERE id = %s",
                (new_rate, seller_id),
            )
            cursor.execute(
                """
                INSERT INTO admin_audit_logs (
                    actor_user_id, action, target_type, target_id,
                    before_data, after_data
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    current_admin["id"],
                    "seller.commission_updated",
                    "seller",
                    seller_id,
                    Jsonb({"commission_rate_percent": str(old_rate) if old_rate is not None else None}),
                    Jsonb({"commission_rate_percent": str(new_rate)}),
                ),
            )

    return {
        "seller_id": seller_id,
        "commission_rate_percent": str(new_rate),
    }


@router.get("/products")
def list_products(limit: PageSize = 25, offset: PageOffset = 0):
    return read_page(
        """
        SELECT p.id, p.name, s.store_name,
               u.full_name AS seller_name, u.email AS seller_email,
               c.name AS category_name, p.price::text AS price,
               p.stock, p.is_active, p.admin_hidden_at,
               (SELECT t.id FROM support_threads AS t
                WHERE t.kind = 'product_moderation' AND t.product_id = p.id)
                   AS moderation_thread_id
        FROM products AS p
        JOIN sellers AS s ON s.id = p.seller_id
        JOIN users AS u ON u.id = s.owner_user_id
        LEFT JOIN categories AS c ON c.id = p.category_id
        ORDER BY p.id DESC
        LIMIT %s OFFSET %s
        """,
        (), limit, offset,
    )


@router.patch("/products/{product_id}/remove")
def remove_product_from_sale(
    product_id: int,
    data: ProductRemoval,
    current_admin: dict = Depends(require_admin),
):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT p.id, p.name, p.is_active, p.admin_hidden_at,
                       s.owner_user_id
                FROM products AS p
                JOIN sellers AS s ON s.id = p.seller_id
                WHERE p.id = %s
                FOR UPDATE OF p
                """,
                (product_id,),
            )
            product = cursor.fetchone()
            if product is None:
                raise HTTPException(status_code=404, detail="Ürün bulunamadı.")
            if product["admin_hidden_at"] is not None:
                raise HTTPException(status_code=409, detail="Ürün zaten admin tarafından yayından kaldırılmış.")

            cursor.execute(
                """
                UPDATE products
                SET is_active = FALSE,
                    admin_hidden_at = NOW(),
                    admin_hidden_by = %s,
                    admin_hidden_reason = %s
                WHERE id = %s
                """,
                (current_admin["id"], data.reason, product_id),
            )
            cursor.execute(
                """
                INSERT INTO seller_notifications (
                    recipient_user_id, actor_user_id, product_id, kind, reason
                ) VALUES (%s, %s, %s, 'product_removed_by_admin', %s)
                """,
                (product["owner_user_id"], current_admin["id"], product_id, data.reason),
            )
            cursor.execute(
                """
                INSERT INTO support_threads (kind, seller_user_id, product_id)
                VALUES ('product_moderation', %s, %s)
                ON CONFLICT DO NOTHING RETURNING id
                """,
                (product["owner_user_id"], product_id),
            )
            created_thread = cursor.fetchone()
            if created_thread is None:
                cursor.execute(
                    "SELECT id FROM support_threads WHERE kind = 'product_moderation' AND product_id = %s",
                    (product_id,),
                )
                thread_id = cursor.fetchone()["id"]
            else:
                thread_id = created_thread["id"]
            cursor.execute(
                """
                INSERT INTO support_messages (thread_id, sender_user_id, body)
                VALUES (%s, %s, %s)
                """,
                (thread_id, current_admin["id"], f"Ürün #{product_id} yayından kaldırıldı. Gerekçe: {data.reason}"),
            )
            cursor.execute("UPDATE support_threads SET updated_at = NOW() WHERE id = %s", (thread_id,))
            cursor.execute(
                """
                INSERT INTO admin_audit_logs (
                    actor_user_id, action, target_type, target_id,
                    before_data, after_data, reason
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    current_admin["id"], "product.removed_by_admin", "product", product_id,
                    Jsonb({"is_active": product["is_active"], "admin_hidden": False}),
                    Jsonb({"is_active": False, "admin_hidden": True}),
                    data.reason,
                ),
            )

    return {
        "id": product_id,
        "name": product["name"],
        "is_active": False,
        "admin_hidden": True,
        "reason": data.reason,
        "thread_id": thread_id,
    }


@router.patch("/products/{product_id}/restore")
def restore_product_to_sale(
    product_id: int,
    data: ProductRestore,
    current_admin: dict = Depends(require_admin),
):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT p.id, p.name, p.admin_hidden_at, p.admin_hidden_reason,
                       s.owner_user_id
                FROM products AS p
                JOIN sellers AS s ON s.id = p.seller_id
                WHERE p.id = %s
                FOR UPDATE OF p
                """,
                (product_id,),
            )
            product = cursor.fetchone()
            if product is None:
                raise HTTPException(status_code=404, detail="Ürün bulunamadı.")
            if product["admin_hidden_at"] is None:
                raise HTTPException(status_code=409, detail="Ürün admin tarafından yayından kaldırılmamış.")

            cursor.execute(
                """
                UPDATE products
                SET is_active = TRUE, admin_hidden_at = NULL,
                    admin_hidden_by = NULL, admin_hidden_reason = NULL
                WHERE id = %s
                """,
                (product_id,),
            )
            cursor.execute(
                "SELECT id FROM support_threads WHERE kind = 'product_moderation' AND product_id = %s",
                (product_id,),
            )
            thread = cursor.fetchone()
            if thread is None:
                cursor.execute(
                    """
                    INSERT INTO support_threads (kind, seller_user_id, product_id)
                    VALUES ('product_moderation', %s, %s)
                    RETURNING id
                    """,
                    (product["owner_user_id"], product_id),
                )
                thread = cursor.fetchone()
            cursor.execute(
                """
                INSERT INTO support_messages (thread_id, sender_user_id, body)
                VALUES (%s, %s, %s)
                """,
                (thread["id"], current_admin["id"], f"Ürün #{product_id} yeniden yayına alındı. {data.message}"),
            )
            cursor.execute("UPDATE support_threads SET updated_at = NOW() WHERE id = %s", (thread["id"],))
            cursor.execute(
                """
                INSERT INTO admin_audit_logs (
                    actor_user_id, action, target_type, target_id,
                    before_data, after_data, reason
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    current_admin["id"], "product.restored_by_admin", "product", product_id,
                    Jsonb({"is_active": False, "admin_hidden": True, "reason": product["admin_hidden_reason"]}),
                    Jsonb({"is_active": True, "admin_hidden": False}), data.message,
                ),
            )

    return {"id": product_id, "name": product["name"], "is_active": True,
            "admin_hidden": False, "thread_id": thread["id"]}


@router.get("/phones")
def list_phones(limit: PageSize = 25, offset: PageOffset = 0):
    return read_page(
        """
        SELECT m.id, b.name AS brand_name, m.name AS model_name,
               COUNT(pcm.product_id) AS compatible_products
        FROM phone_models AS m
        JOIN phone_brands AS b ON b.id = m.brand_id
        LEFT JOIN product_compatible_models AS pcm ON pcm.phone_model_id = m.id
        GROUP BY m.id, b.name, m.name
        ORDER BY b.name, m.name, m.id
        LIMIT %s OFFSET %s
        """,
        (), limit, offset,
    )


@router.get("/sales")
def list_sales(limit: PageSize = 25, offset: PageOffset = 0):
    return read_page(
        """
        WITH paid_page AS (
            SELECT id, customer_id, total_amount, created_at
            FROM orders
            WHERE status = 'paid'
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        )
        SELECT o.id, u.full_name AS customer_name, o.created_at,
               o.total_amount::text AS total_amount,
               COALESCE(lines.items, '[]'::jsonb) AS items
        FROM paid_page AS o
        JOIN users AS u ON u.id = o.customer_id
        CROSS JOIN LATERAL (
            SELECT jsonb_agg(jsonb_build_object(
                'id', oi.id,
                'store_name', s.store_name,
                'product_name', oi.product_name,
                'quantity', oi.quantity,
                'unit_price', oi.unit_price::text,
                'shipping_status', oi.shipping_status
            ) ORDER BY oi.id) AS items
            FROM order_items AS oi
            JOIN sellers AS s ON s.id = oi.seller_id
            WHERE oi.order_id = o.id
        ) AS lines
        ORDER BY o.id DESC
        """,
        (), limit, offset,
    )
