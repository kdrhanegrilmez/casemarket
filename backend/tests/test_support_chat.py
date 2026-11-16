import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from main import app
from routers.support import MessageCreate, contact_customer_support, get_thread, list_admin_threads


class FakeCursor:
    def __init__(self, rows=(), many=()):
        self.rows = iter(rows)
        self.many = iter(many)
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params):
        self.queries.append((" ".join(sql.upper().split()), params))

    def fetchone(self):
        return next(self.rows)

    def fetchall(self):
        return next(self.many)


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, error_type, *_):
        self.committed = error_type is None
        return False

    def cursor(self, **_):
        return self.fake_cursor


class SupportChatTests(unittest.TestCase):
    def test_support_and_restore_routes_are_registered(self):
        paths = app.openapi()["paths"]
        self.assertIn("patch", paths["/api/admin/products/{product_id}/restore"])
        self.assertIn("post", paths["/api/support/products/{product_id}/question"])
        self.assertIn("get", paths["/api/support/admin/threads"])

    def test_blank_message_is_rejected(self):
        with self.assertRaises(ValidationError):
            MessageCreate(message="   ")

    def test_customer_message_is_attached_to_customer_thread(self):
        cursor = FakeCursor([{"id": 14}, {"id": 51, "created_at": datetime.now(timezone.utc)}])
        connection = FakeConnection(cursor)
        with patch("routers.support.get_connection", return_value=connection):
            result = contact_customer_support(MessageCreate(message="  Siparişim hakkında soru  "), {"id": 7, "role": "customer"})

        self.assertTrue(connection.committed)
        self.assertEqual(result["thread_id"], 14)
        self.assertEqual(cursor.queries[0][1], ("customer_support", 7, None, None))
        self.assertEqual(cursor.queries[1][1], (14, 7, "Siparişim hakkında soru"))

    def test_other_customer_cannot_read_thread(self):
        cursor = FakeCursor([
            {"id": 14, "kind": "customer_support"},
            {"customer_user_id": 7, "seller_user_id": None},
        ])
        with patch("routers.support.get_connection", return_value=FakeConnection(cursor)):
            with self.assertRaises(HTTPException) as error:
                get_thread(14, {"id": 8, "role": "customer"})

        self.assertEqual(error.exception.status_code, 404)

    def test_seller_cannot_use_customer_support(self):
        with self.assertRaises(HTTPException) as error:
            contact_customer_support(MessageCreate(message="Yardım"), {"id": 7, "role": "seller"})
        self.assertEqual(error.exception.status_code, 403)

    def test_admin_inboxes_keep_customer_and_seller_channels_separate(self):
        customer_cursor = FakeCursor(many=[[]])
        seller_cursor = FakeCursor(many=[[]])
        with patch("routers.support.get_connection", side_effect=[FakeConnection(customer_cursor), FakeConnection(seller_cursor)]):
            list_admin_threads("customer", {"id": 2, "role": "admin"})
            list_admin_threads("seller", {"id": 2, "role": "admin"})

        self.assertEqual(customer_cursor.queries[0][1], (["customer_support"],))
        self.assertEqual(seller_cursor.queries[0][1], (["seller_support", "product_moderation"],))


if __name__ == "__main__":
    unittest.main()
