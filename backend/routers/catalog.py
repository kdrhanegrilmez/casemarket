from typing import Any

from fastapi import APIRouter, HTTPException

from database import get_connection


router = APIRouter(prefix="/api/catalog", tags=["catalog"])


def _serialize_product(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "price": str(row[3]),
        "stock": row[4],
        "image_url": row[5],
        "store_name": row[6],
    }


@router.get("/products")
def get_catalog_products():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.description,
                    p.price,
                    p.stock,
                    p.image_url,
                    s.store_name
                FROM products AS p
                JOIN sellers AS s ON s.id = p.seller_id
                WHERE p.is_active = TRUE
                ORDER BY p.id
                """
            )
            rows = cursor.fetchall()

    return [_serialize_product(row) for row in rows]



#Tek bir ürünün detaylarını getir


# Tek bir urunun detaylarini getirir.

@router.get("/products/{product_id}")
def get_catalog_product_detail(product_id: int):

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.description,
                    p.price,
                    p.stock,
                    p.image_url,
                    s.store_name
                FROM products AS p
                JOIN sellers AS s
                    ON p.seller_id = s.id
                WHERE
                    p.id = %s
                    AND p.is_active = TRUE
                """,
                (product_id,),
            )

            product = cursor.fetchone()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Urun bulunamadi.",
        )

    return {
        "id": product[0],
        "name": product[1],
        "description": product[2],
        "price": str(product[3]),
        "stock": product[4],
        "image_url": product[5],
        "store_name": product[6],
    }
