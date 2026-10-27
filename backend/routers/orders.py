from decimal import Decimal
from statistics import quantiles

from fastapi import APIRouter, Depends, HTTPException

from core.dependencies import get_current_user
from database import get_connection
from routers import seller
from schemas.orders import OrderCreate

router = APIRouter(
    prefix="/api/orders",
    tags=["orders"],
)


# 1. GIRIS YAPAN KULLANICININ SIPARIS OLUSTURMASI

@router.post("",status_code=201)
def create_order(
    data:OrderCreate,
    current_user: dict =Depends(get_current_user),
):
    # Ayni urun bir sipariste iki kez gonderilmesin.

    product_ids =[item.product_id for item in data.items]

    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(
            status_code=422,
            detail="Ayni urunu sipariste birden fazla kez gondermeyin.",
        )

    total_amount= Decimal("0.00")
    order_products=[]

    with get_connection() as connection:
        with connection.cursor() as cursor:

            #data.items içindeki elemanları product_id değerine göre küçükten büyüğe sıralar
            for item in sorted(
                data.items,
                key=lambda item: item.product_id,
            ):
                cursor.execute(
                    """
                    SELECT
                        id,
                        seller_id,
                        name,
                        price,
                        stock,
                        is_active
                    FROM products
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (item.product_id,),

                )
                product=cursor.fetchone()

                if product is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Aradığınız ürün bulunmadı: {item.product_id}",
                    )
                (
                    product_id,
                    seller_id,
                    product_name,
                    unit_price,
                    stock,
                    is_active,
                )= product

                if not is_active:
                    raise HTTPException(
                        status_code=409,
                        detail="Aradığınız ürün satış dışı: {product_name}",
                    )

                if stock< item.quantity:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Stoklar yetersiz: {product_name}"
                    )

                #Fiyat frontend'den deil veritabanından gelmeli

                total_amount += unit_price * item.quantity

                order_products.append(
                    {
                        "product_id": product_id,
                        "seller_id": seller_id,
                        "product_name": product_name,
                        "unit_price": unit_price,
                        "quantity": item.quantity,
                    }
                )

                # orders.total_amount numeric(10,2) oldugu icin.
                if total_amount > Decimal("99999999.99"):
                    raise HTTPException(
                        status_code=422,
                        detail="Sipariş tutarı izin verilen sınırı aşıyor"

                    )

                # Once siparisin ana kaydı oluşturulmalı.

                cursor.execute(
                    """
                    INSERT INTO orders(
                        customer_id,
                        total_amount,
                        status
                    ) 
                    VALUES (%s,%s,'pending')
                        RETURNING id, status
                    """,
                    (current_user["id"],
                     total_amount,),
                )

                order_id, order_status = cursor.fetchone()

                # Her urunun stokunu azalt ve siparis satirini kaydet.
                for item in order_products:
                    cursor.execute(
                        """
                        UPDATE products 
                        SET stock=stock-%s 
                        WHERE id=%s
                        """,(
                            item["quantity"],
                            item["product_id"],
                        ),
                    )

                    cursor.execute(
                        """
                                INSERT INTO order_items (
                                       order_id,
                                      product_id,
                                      seller_id,
                                     product_name,
                                      quantity,
                                      unit_price
                                    )
                                    VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            order_id,
                            item["product_id"],
                            item["seller_id"],
                            item["product_name"],
                            item["quantity"],
                            item["unit_price"],
                        ),
                    )

    return {
        "id":order_id,
        "status":order_status,
        "total_amount":str(total_amount),
        "items":[
            {
                "product_id":item["product_id"],
                "product_name":item["product_name"],
                "quantity":item["quantity"],
                "unit_price": str(item["unit_price"]),
            }
            for item in order_products
        ],
    }



#2 Giriş yapan Kullanıcının sipariş geçmişi


# 2. GIRIS YAPAN KULLANICININ SIPARIS GECMISI

@router.get("/mine")
def get_my_orders(
    current_user: dict = Depends(get_current_user),
):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    o.id,
                    o.total_amount,
                    o.status,
                    o.created_at,
                    oi.product_id,
                    oi.product_name,
                    oi.quantity,
                    oi.unit_price
                FROM orders AS o
                LEFT JOIN order_items AS oi
                    ON oi.order_id = o.id
                WHERE o.customer_id = %s
                ORDER BY o.created_at DESC, o.id DESC, oi.id
                """,
                (current_user["id"],),
            )

            rows = cursor.fetchall()

    orders = []
    orders_by_id = {}

    for row in rows:
        order_id = row[0]

        # Bir siparis birden fazla urun icerebilir.
        # Her siparisi listede yalnizca bir kez olustur.
        if order_id not in orders_by_id:
            order = {
                "id": order_id,
                "total_amount": str(row[1]),
                "status": row[2],
                "created_at": row[3].isoformat(),
                "items": [],
            }

            orders.append(order)
            orders_by_id[order_id] = order

        # Siparisin urunlerini kendi items listesine ekle.
        if row[4] is not None:
            orders_by_id[order_id]["items"].append({
                "product_id": row[4],
                "product_name": row[5],
                "quantity": row[6],
                "unit_price": str(row[7]),
            })

    return orders




# 3. MUSTERININ BEKLEYEN SIPARISINI IPTAL ETMESI

@router.post("/{order_id}/cancel")
def cancel_my_order(
    order_id: int,
    current_user: dict = Depends(get_current_user),
):
    if order_id < 1:
        raise HTTPException(
            status_code=400,
            detail="Geçersiz sipariş numarası.",
        )

    with get_connection() as connection:
        try:
            with connection.cursor() as cursor:

                # Siparisi kilitleyerek ayni anda iki kez
                # iptal edilmesini engelliyoruz.
                cursor.execute(
                    """
                    SELECT id, status
                    FROM orders
                    WHERE id = %s AND customer_id = %s
                    FOR UPDATE
                    """,
                    (order_id, current_user["id"]),
                )

                order = cursor.fetchone()

                if order is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Sipariş bulunamadı.",
                    )

                # Odeme beklemeyen siparis iptal edilemez.
                if order[1] != "pending":
                    raise HTTPException(
                        status_code=409,
                        detail="Bu sipariş artık iptal edilemez.",
                    )

                # Siparisteki urunleri ve adetlerini getir.
                cursor.execute(
                    """
                    SELECT product_id, SUM(quantity)
                    FROM order_items
                    WHERE order_id = %s
                    GROUP BY product_id
                    ORDER BY product_id
                    """,
                    (order_id,),
                )

                items = cursor.fetchall()

                if not items:
                    raise HTTPException(
                        status_code=409,
                        detail="Sipariş ürünleri bulunamadı.",
                    )

                # Iptal edilen urunleri stoga geri ekle.
                for product_id, quantity in items:
                    cursor.execute(
                        """
                        UPDATE products
                        SET stock = stock + %s
                        WHERE id = %s
                        RETURNING id
                        """,
                        (quantity, product_id),
                    )

                    if cursor.fetchone() is None:
                        raise HTTPException(
                            status_code=409,
                            detail="Ürün bulunamadığı için sipariş iptal edilemedi.",
                        )

                # Siparis durumunu iptal edildi olarak degistir.
                cursor.execute(
                    """
                    UPDATE orders
                    SET status = 'canceled'
                    WHERE id = %s
                    """,
                    (order_id,),
                )

            # Tum islemler basariliysa kaydet.
            connection.commit()

        except Exception:
            # Herhangi bir hata olursa degisiklikleri geri al.
            connection.rollback()
            raise

    return {
        "id": order_id,
        "status": "canceled",
        "message": "Sipariş iptal edildi. Stoklar geri yüklendi.",
    }



# 4. MUSTERININ DEMO ODEME YAPMASI

@router.post("/{order_id}/pay-demo")
def pay_demo_order(
    order_id: int,
    current_user: dict = Depends(get_current_user),
):
    if order_id < 1:
        raise HTTPException(
            status_code=400,
            detail="Geçersiz sipariş numarası.",
        )

    with get_connection() as connection:
        try:
            with connection.cursor() as cursor:

                # Siparisi kilitle ve giris yapan
                # kullaniciya ait oldugunu kontrol et.
                cursor.execute(
                    """
                    SELECT id, status
                    FROM orders
                    WHERE id = %s AND customer_id = %s
                    FOR UPDATE
                    """,
                    (order_id, current_user["id"]),
                )

                order = cursor.fetchone()

                if order is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Sipariş bulunamadı.",
                    )

                # Yalnizca bekleyen siparisler odenebilir.
                if order[1] != "pending":
                    raise HTTPException(
                        status_code=409,
                        detail="Bu sipariş için demo ödeme yapılamaz.",
                    )

                # Gercek odeme almiyoruz.
                # Yalnizca siparis durumunu degistiriyoruz.
                cursor.execute(
                    """
                    UPDATE orders
                    SET status = 'paid'
                    WHERE id = %s
                    RETURNING id, status
                    """,
                    (order_id,),
                )

                paid_order = cursor.fetchone()

            # Basarili islemleri veritabanina kaydet.
            connection.commit()

        except Exception:
            # Hata olursa tum degisiklikleri geri al.
            connection.rollback()
            raise

    return {
        "id": paid_order[0],
        "status": paid_order[1],
        "message": "Demo ödeme başarılı. Gerçek ödeme alınmadı.",
    }

