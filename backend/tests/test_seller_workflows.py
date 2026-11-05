import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException

from routers.seller_orders import ShippingStatusUpdate, get_seller_orders, update_shipping_status
from routers.seller_products import create_my_product, get_my_products, update_my_product
from schemas.seller_products import SellerProductCreate, SellerProductUpdate


class Cursor:
    def __init__(self, one=(), many=()):
        self.one = iter(one)
        self.many = iter(many)
        self.queries = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True

    def execute(self, sql, params):
        if self.closed:
            raise RuntimeError("Cursor kapalı")
        self.queries.append((" ".join(sql.upper().split()), params))

    def fetchone(self):
        return next(self.one)

    def fetchall(self):
        return next(self.many)


class Connection:
    def __init__(self, cursor):
        self.test_cursor = cursor
        self.committed = False
        self.rolled_back = False

    def __enter__(self):
        return self

    def __exit__(self, error_type, *_):
        self.committed = error_type is None
        self.rolled_back = error_type is not None

    def cursor(self):
        return self.test_cursor


SELLER = {"id": 7, "role": "seller"}


class SellerProductTests(unittest.TestCase):
    def test_create_saves_models_before_cursor_closes(self):
        cursor = Cursor(
            one=[(3,), (1,), (12, 3, 1, "Kılıf", "Açıklama", Decimal("49.90"), 4, "/case.jpg")],
            many=[[(18,)]],
        )
        connection = Connection(cursor)
        data = SellerProductCreate(name="Kılıf", description="Açıklama", price="49.90", stock=4, category_id=1, model_ids=[18], image_url="/case.jpg")
        with patch("routers.seller_products.get_connection", return_value=connection):
            result = create_my_product(data, SELLER)
        self.assertEqual(result["model_ids"], [18])
        self.assertTrue(connection.committed)
        self.assertTrue(any("INSERT INTO PRODUCT_COMPATIBLE_MODELS" in sql for sql, _ in cursor.queries))

    def test_list_returns_compatible_model_ids(self):
        cursor = Cursor(many=[[(12, "Kılıf", Decimal("49.90"), 4, 1, True, "Mağaza", "/case.jpg", [18, 19])]])
        with patch("routers.seller_products.get_connection", return_value=Connection(cursor)):
            result = get_my_products(SELLER)
        self.assertEqual(result[0]["model_ids"], [18, 19])

    def test_invalid_model_aborts_atomic_update(self):
        cursor = Cursor(one=[(12,), (1,)], many=[[]])
        connection = Connection(cursor)
        data = SellerProductUpdate(price="49.90", category_id=1, model_ids=[999])
        with patch("routers.seller_products.get_connection", return_value=connection):
            with self.assertRaises(HTTPException) as error:
                update_my_product(12, data, SELLER)
        self.assertEqual(error.exception.status_code, 400)
        self.assertTrue(connection.rolled_back)
        self.assertFalse(any(sql.startswith("UPDATE PRODUCTS") for sql, _ in cursor.queries))


class SellerShippingTests(unittest.TestCase):
    def test_seller_order_list_groups_only_queried_items(self):
        created_at = datetime(2026, 11, 5, tzinfo=timezone.utc)
        cursor = Cursor(many=[[
            (4, "paid", created_at, "Ankara", 10, 12, "Kılıf A", 2, Decimal("50.00"), "pending"),
            (4, "paid", created_at, "Ankara", 11, 13, "Kılıf B", 1, Decimal("75.00"), "preparing"),
        ]])
        with patch("routers.seller_orders.get_connection", return_value=Connection(cursor)):
            orders = get_seller_orders(SELLER)
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]["seller_total"], "175.00")
        self.assertEqual([item["id"] for item in orders[0]["items"]], [10, 11])
        self.assertIn("S.OWNER_USER_ID = %S", cursor.queries[0][0])

    def test_only_paid_owned_item_advances_one_step(self):
        cursor = Cursor(one=[("pending", "paid", "Ankara, Türkiye")])
        connection = Connection(cursor)
        with patch("routers.seller_orders.get_connection", return_value=connection):
            result = update_shipping_status(4, 10, ShippingStatusUpdate(status="preparing"), SELLER)
        self.assertEqual(result["shipping_status"], "preparing")
        self.assertTrue(connection.committed)
        self.assertTrue(any(sql.startswith("UPDATE ORDER_ITEMS") for sql, _ in cursor.queries))

    def test_other_sellers_item_is_not_found(self):
        cursor = Cursor(one=[None])
        connection = Connection(cursor)
        with patch("routers.seller_orders.get_connection", return_value=connection):
            with self.assertRaises(HTTPException) as error:
                update_shipping_status(4, 10, ShippingStatusUpdate(status="preparing"), SELLER)
        self.assertEqual(error.exception.status_code, 404)
        self.assertFalse(any(sql.startswith("UPDATE ORDER_ITEMS") for sql, _ in cursor.queries))

    def test_shipping_requires_address(self):
        cursor = Cursor(one=[("preparing", "paid", None)])
        connection = Connection(cursor)
        with patch("routers.seller_orders.get_connection", return_value=connection):
            with self.assertRaises(HTTPException) as error:
                update_shipping_status(4, 10, ShippingStatusUpdate(status="shipped"), SELLER)
        self.assertEqual(error.exception.status_code, 409)
