
from fastapi import APIRouter, Depends, HTTPException

from core.dependencies import get_current_user
from database import get_connection
from schemas.seller_products import (SellerProductCreate, SellerProductUpdate, SellerProductVisibilityUpdate)


router = APIRouter(
    prefix="/api/sellers/me/products",
    tags=["seller-products"],
)


# 1. SATICININ KENDI MAGAZASINA URUN EKLEMESI

@router.post("", status_code=201)
def create_my_product(
    data: SellerProductCreate,
    current_user: dict = Depends(get_current_user),
):
    # Giris yapan kullanicinin rolunu kontrol et.
    if current_user["role"] != "seller":
        raise HTTPException(
            status_code=403,
            detail="Bu islem icin satici hesabi gerekli.",
        )

    name = data.name.strip()

    if len(name) < 3:
        raise HTTPException(
            status_code=422,
            detail="Urun adi en az 3 karakter olmali.",
        )

    description = (
        data.description.strip()
        if data.description is not None
        else None
    )

    with get_connection() as connection:
        with connection.cursor() as cursor:

            # Kullaniciya ait magazayi bul.
            cursor.execute(
                """
                SELECT id
                FROM sellers
                WHERE owner_user_id = %s
                """,
                (current_user["id"],),
            )

            seller = cursor.fetchone()

            if seller is None:
                raise HTTPException(
                    status_code=404,
                    detail="Satici magazasi bulunamadi.",
                )

            seller_id = seller[0]

            # Kategori belirtilmisse veritabaninda kontrol et.
            if data.category_id is not None:
                cursor.execute(
                    """
                    SELECT 1
                    FROM categories
                    WHERE id = %s
                    """,
                    (data.category_id,),
                )

                if cursor.fetchone() is None:
                    raise HTTPException(
                        status_code=400,
                        detail="Kategori bulunamadi.",
                    )

            # Urunu gercek products tablosuna kaydet.
            cursor.execute(
                """
                INSERT INTO products
                    (
                        seller_id,
                        category_id,
                        name,
                        description,
                        price,
                        stock
                    )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING
                    id,
                    seller_id,
                    category_id,
                    name,
                    description,
                    price,
                    stock
                """,
                (
                    seller_id,
                    data.category_id,
                    name,
                    description,
                    data.price,
                    data.stock,
                ),
            )

            product = cursor.fetchone()

    return {
        "id": product[0],
        "seller_id": product[1],
        "category_id": product[2],
        "name": product[3],
        "description": product[4],
        "price": str(product[5]),
        "stock": product[6],
    }


# 2. SATICININ KENDI URUNLERINI LISTELEMESI

@router.get("")
def get_my_products(
    current_user: dict = Depends(get_current_user),
):
    # Yalnizca saticilar bu listeyi gorebilir.
    if current_user["role"] != "seller":
        raise HTTPException(
            status_code=403,
            detail="Bu islem icin satici hesabi gerekli.",
        )

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.price,
                    p.stock,
                    p.category_id,
                    p.is_active,
                    s.store_name
                FROM products AS p
                JOIN sellers AS s
                    ON p.seller_id = s.id
                WHERE s.owner_user_id = %s
                ORDER BY p.id DESC
                """,
                (current_user["id"],),
            )

            rows = cursor.fetchall()

    products = []

    for row in rows:
        products.append({
            "id": row[0],
            "name": row[1],
            "price": str(row[2]),
            "stock": row[3],
            "category_id": row[4],
            "is_active": row[5],
            "store_name": row[6],
        })

    return products


#3 Saticinin kendi ürünün güncellemesi


@router.patch("/{product_id}")
def update_my_product(
    product_id: int,
    data: SellerProductUpdate,
    current_user: dict = Depends(get_current_user),
):
    # Yalnizca satici hesaplari urun guncelleyebilir.
    if current_user["role"] != "seller":
        raise HTTPException(
            status_code=403,
            detail="Bu islemi gerceklestirebilmek icin satici hesabi gerekir.",
        )

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE products AS p
                SET
                    price = COALESCE(%s, p.price),
                    stock = COALESCE(%s, p.stock)
                FROM sellers AS s
                WHERE
                    p.id = %s
                    AND p.seller_id = s.id
                    AND s.owner_user_id = %s
                RETURNING
                    p.id,
                    p.name,
                    p.price,
                    p.stock
                """,
                (
                    data.price,
                    data.stock,
                    product_id,
                    current_user["id"],
                ),
            )

            product = cursor.fetchone()

            # Urun bulunamadiginda veya baska saticiya ait oldugunda.
            if product is None:
                raise HTTPException(
                    status_code=404,
                    detail="Urun bulunamadi veya bu urun size ait degil.",
                )

    return {
        "id": product[0],
        "name": product[1],
        "price": str(product[2]),
        "stock": product[3],
    }


# 4. SATICININ URUNU YAYINDAN KALDIRMASI VE YAYINLAMASI

@router.patch("/{product_id}/visibility")
def update_my_product_visibility(
    product_id: int,
    data: SellerProductVisibilityUpdate,
    current_user: dict = Depends(get_current_user),
):
    # Yalnizca saticilar bu islemi yapabilir.
    if current_user["role"] != "seller":
        raise HTTPException(
            status_code=403,
            detail="Bu islem icin satici hesabi gerekli.",
        )

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE products AS p
                SET is_active = %s
                FROM sellers AS s
                WHERE
                    p.id = %s
                    AND p.seller_id = s.id
                    AND s.owner_user_id = %s
                RETURNING
                    p.id,
                    p.name,
                    p.is_active
                """,
                (
                    data.is_active,
                    product_id,
                    current_user["id"],
                ),
            )

            product = cursor.fetchone()

            if product is None:
                raise HTTPException(
                    status_code=404,
                    detail="Urun bulunamadi veya bu urun size ait degil.",
                )

    return {
        "id": product[0],
        "name": product[1],
        "is_active": product[2],
    }
