from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from core.dependencies import get_current_user
from database import get_connection
from schemas.orders import OrderCreate

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("/checkout-demo", status_code=201)
def checkout_demo(data: OrderCreate, user: dict = Depends(get_current_user)):
    if data.address_id is None or data.payment_method_id is None:
        raise HTTPException(status_code=422, detail="Adres ve demo ödeme yöntemi seçmelisin.")
    product_ids = [item.product_id for item in data.items]
    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(status_code=422, detail="Aynı ürün iki kez gönderilemez.")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT recipient, phone, city, district, address_line, postal_code
                FROM user_addresses WHERE id = %s AND user_id = %s""",
                (data.address_id, user["id"]),
            )
            address = cursor.fetchone()
            if address is None:
                raise HTTPException(status_code=404, detail="Seçilen adres bulunamadı.")

            cursor.execute(
                """SELECT brand, last_four, expiry_month, expiry_year
                FROM user_payment_methods WHERE id = %s AND user_id = %s""",
                (data.payment_method_id, user["id"]),
            )
            method = cursor.fetchone()
            if method is None:
                raise HTTPException(status_code=404, detail="Seçilen ödeme yöntemi bulunamadı.")
            brand, last_four, month, year = method
            today = date.today()
            if (year, month) < (today.year, today.month):
                raise HTTPException(status_code=422, detail="Demo kartın son kullanma tarihi geçmiş.")

            shipping_address = ", ".join(str(value) for value in address if value)
            payment_summary = f"{brand} •••• {last_four} (demo)"
            total = Decimal("0.00")
            products = []
            for item in sorted(data.items, key=lambda value: value.product_id):
                cursor.execute(
                    """SELECT id, seller_id, name, price, stock, is_active
                    FROM products WHERE id = %s FOR UPDATE""",
                    (item.product_id,),
                )
                product = cursor.fetchone()
                if product is None:
                    raise HTTPException(status_code=404, detail=f"Ürün bulunamadı: {item.product_id}")
                product_id, seller_id, name, price, stock, active = product
                if not active or stock < item.quantity:
                    raise HTTPException(status_code=409, detail=f"Ürün stokta yok: {name}")
                total += price * item.quantity
                if total > Decimal("99999999.99"):
                    raise HTTPException(status_code=422, detail="Sipariş tutarı sınırı aşıyor.")
                products.append((product_id, seller_id, name, item.quantity, price))

            cursor.execute(
                """INSERT INTO orders
                (customer_id, total_amount, status, shipping_address, payment_method_summary)
                VALUES (%s, %s, 'paid', %s, %s) RETURNING id""",
                (user["id"], total, shipping_address, payment_summary),
            )
            order_id = cursor.fetchone()[0]
            for product_id, seller_id, name, quantity, price in products:
                cursor.execute(
                    "UPDATE products SET stock = stock - %s WHERE id = %s",
                    (quantity, product_id),
                )
                cursor.execute(
                    """INSERT INTO order_items
                    (order_id, product_id, seller_id, product_name, quantity, unit_price)
                    VALUES (%s, %s, %s, %s, %s, %s)""",
                    (order_id, product_id, seller_id, name, quantity, price),
                )

    return {"id": order_id, "status": "paid", "total_amount": str(total),
            "shipping_address": shipping_address, "payment_method_summary": payment_summary}
