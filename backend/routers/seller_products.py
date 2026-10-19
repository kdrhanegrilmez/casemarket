
from fastapi import APIRouter, Depends, HTTPException

from core.dependencies import get_current_user
from database import get_connection
from schemas.seller_products import SellerProductCreate


router = APIRouter(
    prefix="/api/sellers/me/products",
    tags=["seller-products"],
)


@router.post("", status_code=201)
def create_my_product(
    data: SellerProductCreate,
    current_user: dict = Depends(get_current_user),
):
    # 1. Giris yapan kisi satici mi?
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

            # 2. Kullanicinin kendi magazasini bul.
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

            # 3. Kategori secildiyse mevcut mu?
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

            # 4. Urunu gercek products tablosuna ekle.
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
