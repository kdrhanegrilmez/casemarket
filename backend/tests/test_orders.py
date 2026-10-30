
import unittest
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException

from routers.orders import cancel_my_order, create_order, pay_demo_order
from schemas.orders import OrderCreate


# GERCEK POSTGRESQL YERINE KULLANACAGIMIZ SAHTE CURSOR
class FakeCursor:
    def __init__(self, one=(), many=(), fail_on=None):
        self.one = iter(one)
        self.many = iter(many)
        self.fail_on = fail_on
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        normalized = " ".join(sql.upper().split())
        self.queries.append((normalized, params))

        if self.fail_on and self.fail_on in normalized:
            raise RuntimeError("Test icin olusturulmus SQL hatasi")

    def fetchone(self):
        return next(self.one)

    def fetchall(self):
        return next(self.many)

    def count(self, phrase):
        return sum(
            phrase in sql
            for sql, _ in self.queries
        )


# VERITABANI BAGLANTISININ SAHTE HALI
class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor
        self.committed = False
        self.rolled_back = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()

        return False

    def cursor(self):
        return self.fake_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class OrderTests(unittest.TestCase):

    # 1. IKI URUN ICIN TEK SIPARIS OLUSMALI
    def test_two_products_create_one_order(self):
        cursor = FakeCursor(one=[
            (11, 3, "Kilif A", Decimal("100.00"), 5, True),
            (12, 4, "Kilif B", Decimal("75.00"), 8, True),
            (42, "pending"),
        ])

        connection = FakeConnection(cursor)

        data = OrderCreate(items=[
            {"product_id": 11, "quantity": 2},
            {"product_id": 12, "quantity": 1},
        ])

        with patch(
            "routers.orders.get_connection",
            return_value=connection,
        ):
            result = create_order(data, {"id": 5})

        self.assertEqual(result["id"], 42)
        self.assertEqual(result["total_amount"], "275.00")

        # Sadece bir ana siparis kaydi olusturulmali.
        self.assertEqual(
            cursor.count("INSERT INTO ORDERS"),
            1,
        )

        # Iki urun iki farkli siparis satiri olusturmali.
        self.assertEqual(
            cursor.count("INSERT INTO ORDER_ITEMS"),
            2,
        )

        # Her urunun stogu yalnizca bir kez dusmeli.
        updates = [
            params
            for sql, params in cursor.queries
            if sql.startswith("UPDATE PRODUCTS")
        ]

        self.assertEqual(
            updates,
            [(2, 11), (1, 12)],
        )

        self.assertTrue(connection.committed)

    # 2. AYNI URUN IKI KEZ GONDERILEMEMELI
    def test_duplicate_product_is_rejected_before_database(self):
        data = OrderCreate(items=[
            {"product_id": 11, "quantity": 1},
            {"product_id": 11, "quantity": 1},
        ])

        with patch("routers.orders.get_connection") as get_connection:
            with self.assertRaises(HTTPException) as caught:
                create_order(data, {"id": 5})

        self.assertEqual(caught.exception.status_code, 422)

        # Hata veritabanina baglanmadan yakalanmali.
        get_connection.assert_not_called()

    # 3. STOK YETERSIZSE SIPARIS OLUSMAMALI
    def test_insufficient_stock_creates_no_order(self):
        cursor = FakeCursor(one=[
            (11, 3, "Kilif A", Decimal("100.00"), 0, True),
        ])

        connection = FakeConnection(cursor)

        data = OrderCreate(items=[
            {"product_id": 11, "quantity": 1},
        ])

        with patch(
            "routers.orders.get_connection",
            return_value=connection,
        ):
            with self.assertRaises(HTTPException) as caught:
                create_order(data, {"id": 5})

        self.assertEqual(caught.exception.status_code, 409)

        self.assertEqual(
            cursor.count("INSERT INTO ORDERS"),
            0,
        )

        self.assertEqual(
            cursor.count("UPDATE PRODUCTS"),
            0,
        )

        self.assertTrue(connection.rolled_back)

    # 4. SQL HATASINDA ROLLBACK CALISMALI
    def test_sql_failure_rolls_back(self):
        cursor = FakeCursor(
            one=[
                (11, 3, "Kilif A", Decimal("100.00"), 5, True),
                (42, "pending"),
            ],
            fail_on="INSERT INTO ORDER_ITEMS",
        )

        connection = FakeConnection(cursor)

        data = OrderCreate(items=[
            {"product_id": 11, "quantity": 1},
        ])

        with patch(
            "routers.orders.get_connection",
            return_value=connection,
        ):
            with self.assertRaises(RuntimeError):
                create_order(data, {"id": 5})

        self.assertTrue(connection.rolled_back)
        self.assertFalse(connection.committed)

    # 5. SIPARIS IPTALINDE STOKLAR GERI YUKLENMELI
    def test_cancel_restores_product_stocks(self):
        cursor = FakeCursor(
            one=[
                (42, "pending"),
                (11,),
                (12,),
            ],
            many=[
                [(11, 2), (12, 1)],
            ],
        )

        connection = FakeConnection(cursor)

        with patch(
            "routers.orders.get_connection",
            return_value=connection,
        ):
            result = cancel_my_order(42, {"id": 5})

        self.assertEqual(result["status"], "canceled")

        restores = [
            params
            for sql, params in cursor.queries
            if sql.startswith("UPDATE PRODUCTS")
        ]

        self.assertEqual(
            restores,
            [(2, 11), (1, 12)],
        )

        self.assertEqual(
            cursor.count("UPDATE ORDERS"),
            1,
        )

        self.assertTrue(connection.committed)

    # 6. ODENMIS SIPARIS IPTAL EDILEMEMELI
    def test_paid_order_cannot_be_canceled(self):
        cursor = FakeCursor(one=[
            (42, "paid"),
        ])

        connection = FakeConnection(cursor)

        with patch(
            "routers.orders.get_connection",
            return_value=connection,
        ):
            with self.assertRaises(HTTPException) as caught:
                cancel_my_order(42, {"id": 5})

        self.assertEqual(caught.exception.status_code, 409)

        # Stoklara kesinlikle dokunulmamali.
        self.assertEqual(
            cursor.count("UPDATE PRODUCTS"),
            0,
        )

    # 7. DEMO ODEMEDE PENDING DURUMU PAID OLMALI
    def test_payment_changes_pending_to_paid(self):
        cursor = FakeCursor(one=[
            (42, "pending"),
            (42, "paid"),
        ])

        connection = FakeConnection(cursor)

        with patch(
            "routers.orders.get_connection",
            return_value=connection,
        ):
            result = pay_demo_order(42, {"id": 5})

        self.assertEqual(result["status"], "paid")

        self.assertEqual(
            cursor.count("UPDATE ORDERS"),
            1,
        )

        # Odeme yapilirken stok yeniden dusmemeli.
        self.assertEqual(
            cursor.count("UPDATE PRODUCTS"),
            0,
        )

        self.assertTrue(connection.committed)

    # 8. ODENMIS SIPARIS IKINCI KEZ ODENEMEMELI
    def test_paid_order_cannot_be_paid_twice(self):
        cursor = FakeCursor(one=[
            (42, "paid"),
        ])

        connection = FakeConnection(cursor)

        with patch(
            "routers.orders.get_connection",
            return_value=connection,
        ):
            with self.assertRaises(HTTPException) as caught:
                pay_demo_order(42, {"id": 5})

        self.assertEqual(caught.exception.status_code, 409)

        self.assertEqual(
            cursor.count("UPDATE ORDERS"),
            0,
        )


if __name__ == "__main__":
    unittest.main()
