from typing import Any

from fastapi import APIRouter, HTTPException

from database import get_connection


router = APIRouter(prefix="/api/products", tags=["products"])


def _serialize_product(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": row[0],
        "name": row[1],
        "price": str(row[2]),
        "stock": row[3],
        "seller": row[4],
    }


@router.get("")
def get_products():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.price,
                    p.stock,
                    s.store_name
                FROM practice_products AS p
                LEFT JOIN practice_seller AS s
                    ON p.seller_id = s.id
                ORDER BY p.id;
                """
            )
            rows = cursor.fetchall()

    return [_serialize_product(row) for row in rows]


@router.get("/{product_id}")
def get_product(product_id: int):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.price,
                    p.stock,
                    s.store_name
                FROM practice_products AS p
                LEFT JOIN practice_seller AS s
                    ON p.seller_id = s.id
                WHERE p.id = %s;
                """,
                (product_id,),
            )
            row = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Urun bulunamadi!")

    return _serialize_product(row)
