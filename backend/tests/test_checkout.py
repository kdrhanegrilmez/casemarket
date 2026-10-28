import unittest
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException

from routers.checkout import checkout_demo
from schemas.orders import OrderCreate


class FakeCursor:
    def __init__(self, results):
        self.results = iter(results)
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        self.queries.append((sql, params))

    def fetchone(self):
        return next(self.results)


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_instance = cursor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.cursor_instance


class CheckoutTests(unittest.TestCase):
    def test_two_items_create_one_paid_order(self):
        cursor = FakeCursor([
            ("Ada", "5551234567", "İstanbul", "Kadıköy", "Örnek sokak 1", None),
            ("Visa", "1234", 12, 2099),
            (11, 3, "Kılıf A", Decimal("100.00"), 5, True),
            (12, 4, "Kılıf B", Decimal("75.00"), 4, True),
            (42,),
        ])
        data = OrderCreate(items=[{"product_id": 11, "quantity": 2},
                                  {"product_id": 12, "quantity": 1}],
                           address_id=7, payment_method_id=8)
        with patch("routers.checkout.get_connection", return_value=FakeConnection(cursor)):
            order = checkout_demo(data, {"id": 5})

        self.assertEqual(order["status"], "paid")
        self.assertEqual(order["total_amount"], "275.00")
        self.assertEqual(sum("INSERT INTO orders" in sql for sql, _ in cursor.queries), 1)
        self.assertEqual(sum("INSERT INTO order_items" in sql for sql, _ in cursor.queries), 2)
        self.assertEqual(sum("UPDATE products" in sql for sql, _ in cursor.queries), 2)
        self.assertEqual(cursor.queries[0][1], (7, 5))
        self.assertEqual(cursor.queries[1][1], (8, 5))

    def test_address_must_belong_to_user(self):
        cursor = FakeCursor([None])
        data = OrderCreate(items=[{"product_id": 11, "quantity": 1}],
                           address_id=7, payment_method_id=8)
        with patch("routers.checkout.get_connection", return_value=FakeConnection(cursor)):
            with self.assertRaises(HTTPException) as error:
                checkout_demo(data, {"id": 5})
        self.assertEqual(error.exception.status_code, 404)
        self.assertEqual(len(cursor.queries), 1)


if __name__ == "__main__":
    unittest.main()
