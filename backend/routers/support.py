from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from psycopg.rows import dict_row

from core.dependencies import get_current_user, require_admin
from database import get_connection


router = APIRouter(prefix="/api/support", tags=["support"])


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def trim_message(cls, value: str) -> str:
        message = value.strip()
        if not message:
            raise ValueError("Mesaj boş olamaz.")
        return message


class ThreadStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["open", "closed"]


def _require_role(user, role):
    if user["role"] != role:
        raise HTTPException(status_code=403, detail="Bu destek alanına erişim yetkiniz yok.")


def _check_message_limit(cursor, user_id):
    # Aynı kullanıcının eşzamanlı isteklerini sıralı say.
    cursor.execute("SELECT pg_advisory_xact_lock(%s)", (user_id,))
    cursor.execute(
        """SELECT COUNT(*) AS message_count FROM support_messages
           WHERE sender_user_id = %s AND created_at >= NOW() - INTERVAL '1 minute'""",
        (user_id,),
    )
    if cursor.fetchone()["message_count"] >= 10:
        raise HTTPException(status_code=429, detail="Bir dakikada en fazla 10 mesaj gönderebilirsiniz.")


def _create_or_reply(kind, user, message, *, customer_id=None, seller_id=None, product_id=None):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            _check_message_limit(cursor, user["id"])
            cursor.execute(
                """
                INSERT INTO support_threads (kind, customer_user_id, seller_user_id, product_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                RETURNING id
                """,
                (kind, customer_id, seller_id, product_id),
            )
            created = cursor.fetchone()
            if created is None:
                cursor.execute(
                    """
                    SELECT id FROM support_threads
                    WHERE kind = %s
                      AND customer_user_id IS NOT DISTINCT FROM %s
                      AND seller_user_id IS NOT DISTINCT FROM %s
                      AND product_id IS NOT DISTINCT FROM %s
                    """,
                    (kind, customer_id, seller_id, product_id),
                )
                existing = cursor.fetchone()
                if existing is None:
                    raise HTTPException(status_code=409, detail="Konuşma oluşturulamadı.")
                thread_id = existing["id"]
            else:
                thread_id = created["id"]

            cursor.execute(
                """
                INSERT INTO support_messages (thread_id, sender_user_id, body)
                VALUES (%s, %s, %s)
                RETURNING id, created_at
                """,
                (thread_id, user["id"], message),
            )
            sent = cursor.fetchone()
            cursor.execute(
                "UPDATE support_threads SET updated_at = %s, status = 'open', closed_at = NULL WHERE id = %s",
                (sent["created_at"], thread_id),
            )
    return {"thread_id": thread_id, "message_id": sent["id"]}


@router.post("/customer", status_code=201)
def contact_customer_support(data: MessageCreate, user: dict = Depends(get_current_user)):
    _require_role(user, "customer")
    return _create_or_reply("customer_support", user, data.message, customer_id=user["id"])


@router.post("/seller", status_code=201)
def contact_seller_support(data: MessageCreate, user: dict = Depends(get_current_user)):
    _require_role(user, "seller")
    return _create_or_reply("seller_support", user, data.message, seller_id=user["id"])


@router.post("/products/{product_id}/question", status_code=201)
def ask_product_question(
    product_id: int,
    data: MessageCreate,
    user: dict = Depends(get_current_user),
):
    _require_role(user, "customer")
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT s.owner_user_id
                FROM products AS p
                JOIN sellers AS s ON s.id = p.seller_id
                WHERE p.id = %s AND p.is_active = TRUE
                  AND s.approval_status = 'approved'
                """,
                (product_id,),
            )
            product = cursor.fetchone()
    if product is None:
        raise HTTPException(status_code=404, detail="Ürün yayında değil veya bulunamadı.")
    return _create_or_reply(
        "product_question", user, data.message,
        customer_id=user["id"], seller_id=product["owner_user_id"], product_id=product_id,
    )


THREAD_LIST_SQL = """
    SELECT t.id, t.kind, t.product_id, t.customer_user_id, t.seller_user_id,
           t.status, t.closed_at, p.name AS product_name,
           p.admin_hidden_at, p.is_active AS product_is_active,
           c.full_name AS customer_name, c.email AS customer_email,
           s.full_name AS seller_name, s.email AS seller_email,
           t.updated_at, latest.body AS last_message,
           latest_user.role AS last_sender_role,
           (SELECT COUNT(*) FROM support_messages AS unread
            WHERE unread.thread_id = t.id
              AND unread.id > COALESCE(reads.last_read_message_id, 0)
              AND unread.sender_user_id <> %s) AS unread_count
    FROM support_threads AS t
    LEFT JOIN support_thread_reads AS reads ON reads.thread_id = t.id AND reads.user_id = %s
    LEFT JOIN LATERAL (
        SELECT body, sender_user_id FROM support_messages
        WHERE thread_id = t.id ORDER BY id DESC LIMIT 1
    ) AS latest ON TRUE
    LEFT JOIN users AS latest_user ON latest_user.id = latest.sender_user_id
    LEFT JOIN users AS c ON c.id = t.customer_user_id
    LEFT JOIN users AS s ON s.id = t.seller_user_id
    LEFT JOIN products AS p ON p.id = t.product_id
"""


@router.get("/my/threads")
def list_my_threads(
    channel: Literal["support", "questions"] = "support",
    user: dict = Depends(get_current_user),
    status: Literal["open", "closed", "all"] = "open",
):
    if user["role"] == "customer":
        kinds = ["customer_support"] if channel == "support" else ["product_question"]
        owner_column = "t.customer_user_id"
    elif user["role"] == "seller":
        kinds = ["seller_support", "product_moderation"] if channel == "support" else ["product_question"]
        owner_column = "t.seller_user_id"
    else:
        raise HTTPException(status_code=403, detail="Bu destek alanına erişim yetkiniz yok.")

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                THREAD_LIST_SQL + f" WHERE {owner_column} = %s AND t.kind = ANY(%s) AND (%s = 'all' OR t.status = %s) ORDER BY t.updated_at DESC, t.id DESC LIMIT 100",
                (user["id"], user["id"], user["id"], kinds, status, status),
            )
            return [
                {key: value for key, value in row.items() if not key.endswith("_email")}
                for row in cursor.fetchall()
            ]


@router.get("/admin/threads")
def list_admin_threads(
    channel: Literal["customer", "seller"],
    admin: dict = Depends(require_admin),
    status: Literal["open", "closed", "all"] = "open",
):
    kinds = ["customer_support"] if channel == "customer" else ["seller_support", "product_moderation"]
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                THREAD_LIST_SQL + " WHERE t.kind = ANY(%s) AND (%s = 'all' OR t.status = %s) ORDER BY t.updated_at DESC, t.id DESC LIMIT 100",
                (admin["id"], admin["id"], kinds, status, status),
            )
            return cursor.fetchall()


def _get_thread(cursor, thread_id, user):
    cursor.execute(
        THREAD_LIST_SQL + " WHERE t.id = %s",
        (user["id"], user["id"], thread_id),
    )
    thread = cursor.fetchone()
    if thread is None:
        raise HTTPException(status_code=404, detail="Konuşma bulunamadı.")

    allowed = (
        user["role"] == "admin"
        or (user["role"] == "customer" and thread["customer_user_id"] == user["id"])
        or (user["role"] == "seller" and thread["seller_user_id"] == user["id"])
    )
    if not allowed:
        raise HTTPException(status_code=404, detail="Konuşma bulunamadı.")
    return thread


@router.get("/threads/{thread_id}")
def get_thread(thread_id: int, user: dict = Depends(get_current_user)):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            thread = _get_thread(cursor, thread_id, user)
            cursor.execute(
                """
                SELECT m.id, m.sender_user_id, u.full_name AS sender_name,
                       u.role AS sender_role, m.body, m.created_at
                FROM support_messages AS m
                JOIN users AS u ON u.id = m.sender_user_id
                WHERE m.id IN (
                    SELECT id FROM support_messages
                    WHERE thread_id = %s ORDER BY id DESC LIMIT 500
                )
                ORDER BY m.id ASC
                """,
                (thread_id,),
            )
            messages = cursor.fetchall()
            cursor.execute(
                """INSERT INTO support_thread_reads (thread_id, user_id, last_read_message_id)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (thread_id, user_id) DO UPDATE
                   SET last_read_message_id = GREATEST(
                       support_thread_reads.last_read_message_id, EXCLUDED.last_read_message_id)""",
                (thread_id, user["id"], messages[-1]["id"] if messages else 0),
            )
            thread["unread_count"] = 0
    if user["role"] != "admin":
        thread = {key: value for key, value in thread.items() if not key.endswith("_email")}
        messages = [
            {**message, "sender_name": "Admin"} if message["sender_role"] == "admin" else message
            for message in messages
        ]
    return {"thread": thread, "messages": messages}


@router.post("/threads/{thread_id}/messages", status_code=201)
def send_message(
    thread_id: int,
    data: MessageCreate,
    user: dict = Depends(get_current_user),
):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            _get_thread(cursor, thread_id, user)
            _check_message_limit(cursor, user["id"])
            cursor.execute(
                """
                INSERT INTO support_messages (thread_id, sender_user_id, body)
                VALUES (%s, %s, %s)
                RETURNING id, created_at
                """,
                (thread_id, user["id"], data.message),
            )
            message = cursor.fetchone()
            cursor.execute(
                "UPDATE support_threads SET updated_at = %s, status = 'open', closed_at = NULL WHERE id = %s",
                (message["created_at"], thread_id),
            )
    return {"id": message["id"], "thread_id": thread_id, "created_at": message["created_at"]}


def _unread_count(user, *, admin=False):
    if admin:
        _require_role(user, "admin")
    if not admin and user["role"] not in ("customer", "seller"):
        raise HTTPException(status_code=403, detail="Bu destek alanına erişim yetkiniz yok.")
    owner_filter = "TRUE" if admin else (
        "t.customer_user_id = %s" if user["role"] == "customer" else "t.seller_user_id = %s"
    )
    params = (user["id"], user["id"]) if admin else (user["id"], user["id"], user["id"])
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                f"""SELECT COUNT(*) AS unread_count FROM support_messages AS m
                    JOIN support_threads AS t ON t.id = m.thread_id
                    LEFT JOIN support_thread_reads AS r
                      ON r.thread_id = t.id AND r.user_id = %s
                    WHERE m.sender_user_id <> %s
                      AND m.id > COALESCE(r.last_read_message_id, 0)
                      AND {owner_filter}""",
                params,
            )
            return {"unread_count": cursor.fetchone()["unread_count"]}


@router.get("/my/unread-count")
def my_unread_count(user: dict = Depends(get_current_user)):
    return _unread_count(user)


@router.get("/admin/unread-count")
def admin_unread_count(admin: dict = Depends(require_admin)):
    return _unread_count(admin, admin=True)


@router.patch("/threads/{thread_id}/status")
def update_thread_status(
    thread_id: int,
    data: ThreadStatusUpdate,
    admin: dict = Depends(require_admin),
):
    _require_role(admin, "admin")
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            _get_thread(cursor, thread_id, admin)
            cursor.execute(
                """UPDATE support_threads
                   SET status = %s, closed_at = CASE WHEN %s = 'closed' THEN NOW() ELSE NULL END
                   WHERE id = %s RETURNING status, closed_at""",
                (data.status, data.status, thread_id),
            )
            result = cursor.fetchone()
    return {"thread_id": thread_id, **result}
