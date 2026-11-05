from fastapi import APIRouter, Depends, HTTPException

from core.dependencies import get_current_user
from database import get_connection
from schemas.seller_products import (
    SellerProductCreate,
    SellerProductUpdate,
    SellerProductVisibilityUpdate,
    SellerProductCompatibilityUpdate,
)


router = APIRouter(
    prefix="/api/sellers/me/products",
    tags=["seller-products"],
)


def _validate_compatibility(cursor, category_id, model_ids):
    if model_ids and category_id is None:
        raise HTTPException(status_code=422, detail="Telefon modeli seçilen ürün için kılıf türü gereklidir.")
    if category_id is not None:
        cursor.execute("SELECT 1 FROM categories WHERE id = %s", (category_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=400, detail="Kategori bulunamadı.")
    if model_ids:
        cursor.execute("SELECT id FROM phone_models WHERE id = ANY(%s)", (model_ids,))
        missing = set(model_ids) - {row[0] for row in cursor.fetchall()}
        if missing:
            raise HTTPException(status_code=400, detail=f"Geçersiz telefon modeli ID'leri: {sorted(missing)}")


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

    #Boş görsel adresini veritabanında NULL olarak sakla
    image_url = data.image_url.strip() if data.image_url else None

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

            _validate_compatibility(cursor, data.category_id, data.model_ids)

            # Urunu gercek products tablosuna kaydet.

            # Ürünü görsel adresiyle birlikte products tablosuna kaydet.
            cursor.execute(
                """
                INSERT INTO products
                (seller_id,
                 category_id,
                 name,
                 description,
                 price,
                 stock,
                 image_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING
                    id,
                    seller_id,
                    category_id,
                    name,
                    description,
                    price,
                    stock,
                    image_url
                """,
                (
                    seller_id,
                    data.category_id,
                    name,
                    description,
                    data.price,
                    data.stock,
                    image_url,
                ),
            )

            product = cursor.fetchone()
            for model_id in data.model_ids:
                cursor.execute(
                    "INSERT INTO product_compatible_models (product_id, phone_model_id) VALUES (%s, %s)",
                    (product[0], model_id),
                )


    return {
        "id": product[0],
        "seller_id": product[1],
        "category_id": product[2],
        "name": product[3],
        "description": product[4],
        "price": str(product[5]),
        "stock": product[6],
        "image_url": product[7],
        "model_ids": data.model_ids,
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
                    s.store_name,
                    p.image_url,
                    ARRAY(
                        SELECT pcm.phone_model_id
                        FROM product_compatible_models AS pcm
                        WHERE pcm.product_id = p.id
                        ORDER BY pcm.phone_model_id
                    ) AS model_ids
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
            "image_url": row[7],
            "model_ids": row[8],
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

    #Daha önceden ürün adı gönderilmişse, bosluklarini temizle.
    name=data.name.strip() if data.name is not None else None

    if name is not None and len(name)<3:
        raise HTTPException(
            status_code=422,
            detail="Ürün adı en az 3 karakterden oluşmak zorudadır"
        )

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.id FROM products AS p
                JOIN sellers AS s ON s.id = p.seller_id
                WHERE p.id = %s AND s.owner_user_id = %s
                FOR UPDATE OF p
                """,
                (product_id, current_user["id"]),
            )
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="Ürün bulunamadı veya size ait değil.")

            if data.model_ids is not None:
                _validate_compatibility(cursor, data.category_id, data.model_ids)

            # COALESCE: Fiyat, stok ve görsel adresini güncelle.
            #Yeni görsel adresi gönderilirse → onu kaydet.
            #None gönderilirse → eski görsel adresini koru.
            cursor.execute(
                """
                UPDATE products AS p
                SET 
                     name      = COALESCE(%s,p.name),
                    price     = COALESCE(%s, p.price),
                    stock     = COALESCE(%s, p.stock),
                    image_url = COALESCE(%s, p.image_url),
                    category_id = COALESCE(%s, p.category_id) FROM sellers AS s
                WHERE
                    p.id = %s
                  AND p.seller_id = s.id
                  AND s.owner_user_id = %s
                    RETURNING
                    p.id
                    , p.name
                    , p.price
                    , p.stock
                    , p.image_url
                    , p.category_id
                """,
                (
                    name,
                    data.price,
                    data.stock,
                    data.image_url,
                    data.category_id,
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

            if data.model_ids is not None:
                cursor.execute(
                    "DELETE FROM product_compatible_models WHERE product_id = %s",
                    (product_id,),
                )
                for model_id in data.model_ids:
                    cursor.execute(
                        "INSERT INTO product_compatible_models (product_id, phone_model_id) VALUES (%s, %s)",
                        (product_id, model_id),
                    )
            else:
                cursor.execute(
                    "SELECT phone_model_id FROM product_compatible_models WHERE product_id = %s ORDER BY phone_model_id",
                    (product_id,),
                )
                model_ids = [row[0] for row in cursor.fetchall()]

    return {
        "id": product[0],
        "name": product[1],
        "price": str(product[2]),
        "stock": product[3],
        "image_url": product[4],
        "category_id": product[5],
        "model_ids": data.model_ids if data.model_ids is not None else model_ids,
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




# 5. SATICININ URUNUNU TELEFON MODELLERIYLE ESLESTIRMESI

@router.patch("/{product_id}/compatibility")
def update_product_compatibility(
    product_id: int,
    data: SellerProductCompatibilityUpdate,
    current_user: dict = Depends(get_current_user),
):

    #1. Yanlızca satıcı hesapları bu işlemleri yapabilir
    if current_user["role"] != "seller":
        raise HTTPException(
            status_code=403,
            detail="Bu işlem için satıcı hesabı gerekir.",
        )

    with get_connection() as connection:
        with connection.cursor() as cursor:

            #2. Ürün Giriş yapan Satıcıya mı ait
            cursor.execute(
                """
                SELECT p.id
                FROM products AS p 
                JOIN sellers AS s 
                    ON s.id = p.seller_id
                WHERE 
                    p.id = %s
                    AND s.owner_user_id = %s
                FOR UPDATE OF p    
                """,
                (product_id,current_user["id"],),
            )
            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Urun bulunamadi ve bu urun size ait degil.",
                )
            #3. SEÇİLEN KILIF KATEGORİSİ VAR MI ?

            cursor.execute(
                """
                SELECT id
                FROM categories
                WHERE id = %s
                """,
                (data.category_id,),
            )

            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=400,
                    detail="Seçilen Kılıf Kategorisi bulunamadı"
                )

            # 4. Seçilen telefon modelleri gerçekten var mı?
            cursor.execute(
                """
                SELECT id
                FROM phone_models
                WHERE id = ANY (%s)
                """,
                (data.model_ids,),
            )

            existing_model_ids = {
                row[0]
                for row in cursor.fetchall()
            }

            missing_model_ids = (
                    set(data.model_ids) - existing_model_ids
            )

            if missing_model_ids:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Geçersiz telefon modeli ID'leri: "
                        f"{sorted(missing_model_ids)}"
                    ),
                )

            # 5. URUNUN KILIF KATEGORISINI GUNCELLE.
            cursor.execute(
                """
                UPDATE products
                SET category_id = %s
                WHERE id = %s
                """,
                (
                    data.category_id,
                    product_id,
                ),
            )

            # 6. ONCE ESKI MODEL ESLESTIRMELERINI KALDIR.
            cursor.execute(
                """
                DELETE FROM product_compatible_models
                WHERE product_id = %s
                """,
                (product_id,),
            )

            # 7. SECILEN YENI MODELLERI KAYDET.
            for model_id in data.model_ids:
                cursor.execute(
                    """
                    INSERT INTO product_compatible_models (
                        product_id,
                        phone_model_id
                    )
                    VALUES (%s, %s)
                    """,
                    (
                        product_id,
                        model_id,
                    ),
                )


    # with blogu basariyla biterse transaction commit edilir.
    return {
        "product_id": product_id,
        "category_id": data.category_id,
        "model_ids": data.model_ids,
        "message": "Ürün kategorisi ve uyumlu modeller güncellendi.",
    }



