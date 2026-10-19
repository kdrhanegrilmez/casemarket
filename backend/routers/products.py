from typing import Any

from fastapi import APIRouter, HTTPException

from database import get_connection
from schemas.products import ProductCreate, ProductStockUpdate


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


@router.post("", status_code=201)
def create_product(product: ProductCreate):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM practice_seller WHERE id = %s",
                (product.seller_id,),
            )
            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=400,
                    detail="Kayitli satici bulunamadi!",
                )

            cursor.execute(
                """
                INSERT INTO practice_products
                    (name, price, stock, seller_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    product.name,
                    product.price,
                    product.stock,
                    product.seller_id,
                ),
            )
            new_product_id = cursor.fetchone()[0]

    return {
        "message": "Urun basariyla kaydedildi!",
        "id": new_product_id,
        "name": product.name,
        "price": str(product.price),
        "stock": product.stock,
        "seller_id": product.seller_id,
    }


@router.patch("/{product_id}/stock")
def update_product_stock(product_id: int, update: ProductStockUpdate):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE practice_products
                SET stock = %s
                WHERE id = %s
                RETURNING id, name, stock;
                """,
                (update.stock, product_id),
            )
            row = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Urun bulunamadi!")

    return {
        "id": row[0],
        "name": row[1],
        "stock": row[2],
        "message": "Stok basariyla guncellendi!",
    }
