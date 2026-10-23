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


