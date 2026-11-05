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
        "category_id": row[7],
        "model_ids": row[8],
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
                    s.store_name,
                    p.category_id,
                    ARRAY(
                        SELECT pcm.phone_model_id
                        FROM product_compatible_models AS pcm
                        WHERE pcm.product_id = p.id
                        ORDER BY pcm.phone_model_id
                    ) AS model_ids
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
                    s.store_name,
                    p.category_id,
                    ARRAY(
                        SELECT pcm.phone_model_id
                        FROM product_compatible_models AS pcm
                        WHERE pcm.product_id = p.id
                        ORDER BY pcm.phone_model_id
                    ) AS model_ids
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

    return _serialize_product(product)



# 3. KATALOG ICIN TELEFON MARKASI, MODELI VE KILIF TURU FILTRELERI

@router.get("/filters")
def get_catalog_filters():

    # Veritabanindan filtre seceneklerini getir.
    with get_connection() as connection:
        with connection.cursor() as cursor:

            # 1. Telefon markalari ve bu markalara ait modeller.
            cursor.execute(
                """
                SELECT
                    b.id,
                    b.name,
                    m.id,
                    m.name
                FROM phone_brands AS b
                LEFT JOIN phone_models AS m
                    ON m.brand_id = b.id
                ORDER BY b.name, m.name
                """
            )

            phone_rows = cursor.fetchall()

            # 2. Kilif turleri (mevcut categories tablosu).
            cursor.execute(
                """
                SELECT
                    id,
                    name
                FROM categories
                ORDER BY name
                """
            )

            category_rows = cursor.fetchall()

    # SQL sonucunu React icin uygun bir yapiya donustur.
    brands = []
    brands_by_id = {}

    for brand_id, brand_name, model_id, model_name in phone_rows:

        # Her markayi listeye yalnizca bir kez ekle.
        if brand_id not in brands_by_id:
            brand = {
                "id": brand_id,
                "name": brand_name,
                "models": [],
            }

            brands.append(brand)
            brands_by_id[brand_id] = brand

        # Markanin telefon modellerini kendi listesine ekle.
        if model_id is not None:
            brands_by_id[brand_id]["models"].append(
                {
                    "id": model_id,
                    "name": model_name,
                }
            )

    # Kilif turlerini JSON icin sozluk listesine donustur.
    categories = [
        {
            "id": category_id,
            "name": category_name,
        }
        for category_id, category_name in category_rows
    ]

    return {
        "brands": brands,
        "categories": categories,
    }
