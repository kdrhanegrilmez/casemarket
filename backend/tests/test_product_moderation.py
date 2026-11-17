import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from routers.admin_dashboard import ProductRemoval, ProductRestore, remove_product_from_sale, restore_product_to_sale
from routers.seller import mark_notification_read
from routers.seller_products import update_my_product_visibility
from schemas.seller_products import SellerProductVisibilityUpdate


class FakeCursor:
    def __init__(self, rows, fail_message=False):
        self.rows = iter(rows)
        self.fail_message = fail_message
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params):
        normalized = " ".join(sql.upper().split())
        self.queries.append((normalized, params))
        if self.fail_message and normalized.startswith("INSERT INTO SUPPORT_MESSAGES"):
            raise RuntimeError("message failed")

    def fetchone(self):
        return next(self.rows)


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor
        self.committed = False
        self.rolled_back = False

    def __enter__(self):
        return self

    def __exit__(self, error_type, *_):
        self.committed = error_type is None
        self.rolled_back = error_type is not None
        return False

    def cursor(self, **_):
        return self.fake_cursor


class ProductModerationTests(unittest.TestCase):
    def test_reason_is_required(self):
        with self.assertRaises(ValidationError):
            ProductRemoval(reason="   ")
        self.assertEqual(ProductRemoval(reason="  Yanlış kategori  ").reason, "Yanlış kategori")

    def test_removal_writes_only_moderation_message_and_audit_atomically(self):
        cursor = FakeCursor([{
            "id": 12, "name": "Kılıf", "is_active": True,
            "admin_hidden_at": None, "owner_user_id": 7,
        }, {"id": 30}])
        connection = FakeConnection(cursor)
        with patch("routers.admin_dashboard.get_connection", return_value=connection):
            result = remove_product_from_sale(12, ProductRemoval(reason="Yanıltıcı açıklama"), {"id": 2})

        self.assertTrue(connection.committed)
        self.assertFalse(result["is_active"])
        self.assertEqual(len(cursor.queries), 6)
        self.assertIn("UPDATE PRODUCTS SET IS_ACTIVE = FALSE", cursor.queries[1][0])
        self.assertFalse(any("INSERT INTO SELLER_NOTIFICATIONS" in sql for sql, _ in cursor.queries))
        self.assertEqual(result["thread_id"], 30)
        self.assertIn("INSERT INTO SUPPORT_MESSAGES", cursor.queries[3][0])
        self.assertEqual(cursor.queries[3][1], (30, 2, "Ürün #12 yayından kaldırıldı. Gerekçe: Yanıltıcı açıklama"))
        self.assertIn("STATUS = 'OPEN'", cursor.queries[4][0])
        self.assertIn("INSERT INTO ADMIN_AUDIT_LOGS", cursor.queries[5][0])

    def test_admin_can_restore_product_and_reply_in_same_thread(self):
        cursor = FakeCursor([{
            "id": 12, "name": "Kılıf", "admin_hidden_at": datetime.now(timezone.utc),
            "admin_hidden_reason": "Fiyat bilgisi güncelle", "owner_user_id": 7,
        }, {"id": 30}])
        connection = FakeConnection(cursor)
        with patch("routers.admin_dashboard.get_connection", return_value=connection):
            result = restore_product_to_sale(12, ProductRestore(message="Fiyat incelendi, yayınlandı."), {"id": 2})

        self.assertTrue(connection.committed)
        self.assertTrue(result["is_active"])
        self.assertEqual(result["thread_id"], 30)
        self.assertIn("ADMIN_HIDDEN_AT = NULL", cursor.queries[1][0])
        self.assertIn("INSERT INTO SUPPORT_MESSAGES", cursor.queries[3][0])
        self.assertEqual(cursor.queries[3][1], (30, 2, "Ürün #12 yeniden yayına alındı. Fiyat incelendi, yayınlandı."))
        self.assertIn("STATUS = 'OPEN'", cursor.queries[4][0])
        self.assertIn("INSERT INTO ADMIN_AUDIT_LOGS", cursor.queries[5][0])

    def test_repeated_removal_is_rejected(self):
        cursor = FakeCursor([{
            "id": 12, "name": "Kılıf", "is_active": False,
            "admin_hidden_at": datetime.now(timezone.utc), "owner_user_id": 7,
        }])
        with patch("routers.admin_dashboard.get_connection", return_value=FakeConnection(cursor)):
            with self.assertRaises(HTTPException) as error:
                remove_product_from_sale(12, ProductRemoval(reason="Yanıltıcı açıklama"), {"id": 2})
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(len(cursor.queries), 1)

    def test_message_failure_rolls_back_product_change(self):
        cursor = FakeCursor([{
            "id": 12, "name": "Kılıf", "is_active": True,
            "admin_hidden_at": None, "owner_user_id": 7,
        }, {"id": 30}], fail_message=True)
        connection = FakeConnection(cursor)
        with patch("routers.admin_dashboard.get_connection", return_value=connection):
            with self.assertRaises(RuntimeError):
                remove_product_from_sale(12, ProductRemoval(reason="Yanıltıcı açıklama"), {"id": 2})
        self.assertTrue(connection.rolled_back)

    def test_seller_cannot_republish_admin_removed_product(self):
        cursor = FakeCursor([None, (datetime.now(timezone.utc),)])
        with patch("routers.seller_products.get_connection", return_value=FakeConnection(cursor)):
            with self.assertRaises(HTTPException) as error:
                update_my_product_visibility(12, SellerProductVisibilityUpdate(is_active=True), {"id": 7, "role": "seller"})
        self.assertEqual(error.exception.status_code, 409)
        self.assertIn("ADMIN_HIDDEN_AT IS NULL", cursor.queries[0][0])

    def test_seller_can_only_mark_own_notification_read(self):
        cursor = FakeCursor([None])
        with patch("routers.seller.get_connection", return_value=FakeConnection(cursor)):
            with self.assertRaises(HTTPException) as error:
                mark_notification_read(99, {"id": 7, "role": "seller"})

        self.assertEqual(error.exception.status_code, 404)
        self.assertEqual(cursor.queries[0][1], (99, 7))
        self.assertIn("RECIPIENT_USER_ID = %S", cursor.queries[0][0])


if __name__ == "__main__":
    unittest.main()
