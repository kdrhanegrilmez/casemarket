import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from main import app
from routers.support import (
    MessageCreate, ThreadStatusUpdate, admin_unread_count, ask_product_question,
    contact_customer_support, contact_seller_support,
    get_thread, list_admin_threads, list_my_threads, my_unread_count,
    send_message, update_thread_status,
)


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
        self.assertIn("get", paths["/api/support/my/unread-count"])
        self.assertIn("get", paths["/api/support/admin/unread-count"])
        self.assertIn("patch", paths["/api/support/threads/{thread_id}/status"])

    def test_blank_message_is_rejected(self):
        with self.assertRaises(ValidationError):
            MessageCreate(message="   ")

    def test_customer_message_is_attached_to_customer_thread(self):
        cursor = FakeCursor([{"message_count": 0}, {"id": 14}, {"id": 51, "created_at": datetime.now(timezone.utc)}])
        connection = FakeConnection(cursor)
        with patch("routers.support.get_connection", return_value=connection):
            result = contact_customer_support(MessageCreate(message="  Siparişim hakkında soru  "), {"id": 7, "role": "customer"})

        self.assertTrue(connection.committed)
        self.assertEqual(result["thread_id"], 14)
        self.assertEqual(cursor.queries[2][1], ("customer_support", 7, None, None))
        self.assertEqual(cursor.queries[3][1], (14, 7, "Siparişim hakkında soru"))

    def test_other_customer_cannot_read_thread(self):
        cursor = FakeCursor([
            {"id": 14, "kind": "customer_support", "customer_user_id": 7, "seller_user_id": None},
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
            list_admin_threads("customer", {"id": 2, "role": "admin"}, "open")
            list_admin_threads("seller", {"id": 2, "role": "admin"}, "closed")

        self.assertEqual(customer_cursor.queries[0][1], (2, 2, ["customer_support"], "open", "open"))
        self.assertEqual(seller_cursor.queries[0][1], (2, 2, ["seller_support", "product_moderation"], "closed", "closed"))

    def test_thread_read_updates_last_seen_and_hides_admin_identity(self):
        cursor = FakeCursor(
            rows=[{"id": 14, "kind": "customer_support", "customer_user_id": 7,
                   "seller_user_id": None, "store_name": "Kılıf Mağazası", "customer_email": "c@example.com", "seller_email": None}],
            many=[[{"id": 51, "sender_user_id": 2, "sender_name": "Yönetici Adı",
                   "sender_role": "admin", "body": "Merhaba"}]],
        )
        connection = FakeConnection(cursor)
        with patch("routers.support.get_connection", return_value=connection):
            result = get_thread(14, {"id": 7, "role": "customer"})
        self.assertEqual(result["messages"][0]["sender_name"], "Admin")
        self.assertNotIn("customer_email", result["thread"])
        self.assertEqual(result["thread"]["store_name"], "Kılıf Mağazası")
        self.assertEqual(cursor.queries[-1][1], (14, 7, 51))
        self.assertIn("GREATEST", cursor.queries[-1][0])
        self.assertEqual(len(cursor.queries), 3)
        self.assertTrue(connection.committed)

    def test_unread_count_is_scoped_to_customer_or_admin(self):
        customer_cursor = FakeCursor(rows=[{"unread_count": 3}])
        admin_cursor = FakeCursor(rows=[{"unread_count": 8}])
        with patch("routers.support.get_connection", side_effect=[FakeConnection(customer_cursor), FakeConnection(admin_cursor)]):
            self.assertEqual(my_unread_count({"id": 7, "role": "customer"}), {"unread_count": 3})
            self.assertEqual(admin_unread_count({"id": 2, "role": "admin"}), {"unread_count": 8})
        self.assertEqual(customer_cursor.queries[0][1], (7, 7, 7))
        self.assertIn("T.CUSTOMER_USER_ID = %S", customer_cursor.queries[0][0])
        self.assertEqual(admin_cursor.queries[0][1], (2, 2))
        self.assertIn("T.KIND IN ('CUSTOMER_SUPPORT', 'SELLER_SUPPORT', 'PRODUCT_MODERATION')", admin_cursor.queries[0][0])

    def test_my_list_filters_status_and_strips_email(self):
        cursor = FakeCursor(many=[[{"id": 14, "status": "closed", "unread_count": 2,
                                    "last_sender_role": "admin", "customer_email": "secret@example.com"}]])
        with patch("routers.support.get_connection", return_value=FakeConnection(cursor)):
            result = list_my_threads("support", {"id": 7, "role": "customer"}, "closed")
        self.assertEqual(cursor.queries[0][1], (7, 7, 7, ["customer_support"], "closed", "closed"))
        self.assertEqual(result[0]["unread_count"], 2)
        self.assertNotIn("customer_email", result[0])

    def test_message_limit_returns_429_before_insert(self):
        cursor = FakeCursor(rows=[{"message_count": 10}])
        with patch("routers.support.get_connection", return_value=FakeConnection(cursor)):
            with self.assertRaises(HTTPException) as error:
                contact_customer_support(MessageCreate(message="Merhaba"), {"id": 7, "role": "customer"})
        self.assertEqual(error.exception.status_code, 429)
        self.assertFalse(any("INSERT INTO SUPPORT_MESSAGES" in sql for sql, _ in cursor.queries))

    def test_reply_reopens_closed_thread(self):
        cursor = FakeCursor(rows=[
            {"id": 14, "customer_user_id": 7, "seller_user_id": None},
            {"message_count": 0},
            {"id": 52, "created_at": datetime.now(timezone.utc)},
        ])
        with patch("routers.support.get_connection", return_value=FakeConnection(cursor)):
            send_message(14, MessageCreate(message="Yanıt"), {"id": 7, "role": "customer"})
        self.assertIn("STATUS = 'OPEN'", cursor.queries[-1][0])

    def test_admin_can_close_and_reopen_thread(self):
        cursor = FakeCursor(rows=[
            {"id": 14, "customer_user_id": 7, "seller_user_id": None},
            {"status": "closed", "closed_at": datetime.now(timezone.utc)},
        ])
        with patch("routers.support.get_connection", return_value=FakeConnection(cursor)):
            result = update_thread_status(14, ThreadStatusUpdate(status="closed"), {"id": 2, "role": "admin"})
        self.assertEqual(result["status"], "closed")
        self.assertEqual(cursor.queries[-1][1], ("closed", "closed", 14))

    def test_customer_cannot_close_thread(self):
        with self.assertRaises(HTTPException) as error:
            update_thread_status(14, ThreadStatusUpdate(status="closed"), {"id": 7, "role": "customer"})
        self.assertEqual(error.exception.status_code, 403)

    def test_admin_can_reopen_thread_and_clear_closed_at(self):
        cursor = FakeCursor(rows=[{"id": 14}, {"status": "open", "closed_at": None}])
        with patch("routers.support.get_connection", return_value=FakeConnection(cursor)):
            result = update_thread_status(14, ThreadStatusUpdate(status="open"), {"id": 2, "role": "admin"})
        self.assertEqual(result, {"thread_id": 14, "status": "open", "closed_at": None})
        self.assertEqual(cursor.queries[-1][1], ("open", "open", 14))
        self.assertIn("ELSE NULL END", cursor.queries[-1][0])

    def test_status_validation_and_seller_status_permission(self):
        with self.assertRaises(ValidationError):
            ThreadStatusUpdate(status="archived")
        with self.assertRaises(HTTPException) as error:
            update_thread_status(14, ThreadStatusUpdate(status="closed"), {"id": 9, "role": "seller"})
        self.assertEqual(error.exception.status_code, 403)

    def test_missing_thread_and_foreign_seller_cannot_read_or_send(self):
        for row in (None, {"id": 14, "customer_user_id": 7, "seller_user_id": 9}):
            for operation in (get_thread, send_message):
                with self.subTest(row=row, operation=operation.__name__):
                    cursor = FakeCursor(rows=[row])
                    connection = FakeConnection(cursor)
                    with patch("routers.support.get_connection", return_value=connection):
                        with self.assertRaises(HTTPException) as error:
                            if operation is get_thread:
                                operation(14, {"id": 10, "role": "seller"})
                            else:
                                operation(14, MessageCreate(message="Yanıt"), {"id": 10, "role": "seller"})
                    self.assertEqual(error.exception.status_code, 404)
                    self.assertEqual(len(cursor.queries), 1)
                    self.assertFalse(connection.committed)

    def test_empty_thread_read_records_zero_and_admin_keeps_emails(self):
        cursor = FakeCursor(rows=[{"id": 14, "customer_email": "c@example.com", "unread_count": 5}], many=[[]])
        with patch("routers.support.get_connection", return_value=FakeConnection(cursor)):
            result = get_thread(14, {"id": 2, "role": "admin"})
        self.assertEqual(cursor.queries[-1][1], (14, 2, 0))
        self.assertEqual(result["thread"]["unread_count"], 0)
        self.assertEqual(result["thread"]["customer_email"], "c@example.com")

    def test_seller_read_hides_emails_and_admin_name(self):
        cursor = FakeCursor(rows=[{"id": 14, "customer_user_id": None, "seller_user_id": 9,
                                   "seller_email": "s@example.com", "customer_email": None}],
                            many=[[{"id": 52, "sender_role": "admin", "sender_name": "Yönetici"}]])
        with patch("routers.support.get_connection", return_value=FakeConnection(cursor)):
            result = get_thread(14, {"id": 9, "role": "seller"})
        self.assertFalse(any(key.endswith("_email") for key in result["thread"]))
        self.assertEqual(result["messages"][0]["sender_name"], "Admin")
        self.assertEqual(cursor.queries[-1][1], (14, 9, 52))

    def test_seller_unread_includes_only_owned_threads_and_other_senders(self):
        cursor = FakeCursor(rows=[{"unread_count": 4}])
        with patch("routers.support.get_connection", return_value=FakeConnection(cursor)):
            self.assertEqual(my_unread_count({"id": 9, "role": "seller"}), {"unread_count": 4})
        sql, params = cursor.queries[0]
        self.assertEqual(params, (9, 9, 9))
        self.assertIn("T.SELLER_USER_ID = %S", sql)
        self.assertIn("M.SENDER_USER_ID <> %S", sql)
        self.assertIn("M.ID > COALESCE(R.LAST_READ_MESSAGE_ID, 0)", sql)
        self.assertNotIn("T.STATUS =", sql)  # Kapalı konuşmaların okunmamış mesajları da sayılır.

    def test_unread_endpoints_reject_wrong_roles(self):
        for operation, role in ((my_unread_count, "admin"), (admin_unread_count, "customer"), (admin_unread_count, "seller")):
            with self.subTest(operation=operation.__name__, role=role):
                with self.assertRaises(HTTPException) as error:
                    operation({"id": 7, "role": role})
                self.assertEqual(error.exception.status_code, 403)

    def test_default_and_all_status_filters_for_each_inbox(self):
        for role in ("customer", "seller"):
            for channel in ("support", "questions"):
                for status in ("open", "closed", "all"):
                    with self.subTest(role=role, channel=channel, status=status):
                        cursor = FakeCursor(many=[[]])
                        with patch("routers.support.get_connection", return_value=FakeConnection(cursor)):
                            if status == "open":
                                list_my_threads(channel, {"id": 7, "role": role})
                            else:
                                list_my_threads(channel, {"id": 7, "role": role}, status)
                        sql, params = cursor.queries[0]
                        self.assertEqual(params[-2:], (status, status))
                        self.assertIn("(%S = 'ALL' OR T.STATUS = %S)", sql)
                        self.assertIn("UNREAD.SENDER_USER_ID <> %S", sql)
                        self.assertIn("UNREAD.ID > COALESCE(READS.LAST_READ_MESSAGE_ID, 0)", sql)
                        self.assertIn("LAST_SENDER_ROLE", sql)
                        self.assertIn("T.SELLER_USER_ID = %S" if role == "seller" else "T.CUSTOMER_USER_ID = %S", sql)
                        self.assertEqual(params[3], ["product_question"] if channel == "questions" else
                                         ["customer_support"] if role == "customer" else ["seller_support", "product_moderation"])
        cursor = FakeCursor(many=[[{"customer_email": "c@example.com"}]])
        with patch("routers.support.get_connection", return_value=FakeConnection(cursor)):
            result = list_admin_threads("customer", {"id": 2, "role": "admin"}, "all")
        self.assertEqual(cursor.queries[0][1][-2:], ("all", "all"))
        self.assertEqual(result[0]["customer_email"], "c@example.com")

    def test_tenth_message_is_allowed_but_reply_limit_rolls_back(self):
        for count in (9, 10):
            with self.subTest(count=count):
                cursor = FakeCursor(rows=[{"id": 14, "customer_user_id": 7, "seller_user_id": None},
                                          {"message_count": count}, {"id": 52, "created_at": datetime.now(timezone.utc)}])
                connection = FakeConnection(cursor)
                with patch("routers.support.get_connection", return_value=connection):
                    if count == 9:
                        self.assertEqual(send_message(14, MessageCreate(message="Yanıt"), {"id": 7, "role": "customer"})["id"], 52)
                    else:
                        with self.assertRaises(HTTPException) as error:
                            send_message(14, MessageCreate(message="Yanıt"), {"id": 7, "role": "customer"})
                        self.assertEqual(error.exception.status_code, 429)
                self.assertEqual(connection.committed, count == 9)
                self.assertIn("PG_ADVISORY_XACT_LOCK", cursor.queries[1][0])
                self.assertIn("INTERVAL '1 MINUTE'", cursor.queries[2][0])

    def test_seller_contact_reuses_thread_and_reopens_it(self):
        cursor = FakeCursor(rows=[{"message_count": 0}, None, {"id": 14},
                                  {"id": 52, "created_at": datetime.now(timezone.utc)}])
        with patch("routers.support.get_connection", return_value=FakeConnection(cursor)):
            result = contact_seller_support(MessageCreate(message="Yardım"), {"id": 9, "role": "seller"})
        self.assertEqual(result["thread_id"], 14)
        self.assertEqual(cursor.queries[2][1], ("seller_support", None, 9, None))
        self.assertIn("STATUS = 'OPEN', CLOSED_AT = NULL", cursor.queries[-1][0])

    def test_product_question_checks_availability_and_uses_message_limit(self):
        product_cursor = FakeCursor(rows=[{"owner_user_id": 9}])
        message_cursor = FakeCursor(rows=[{"message_count": 10}])
        with patch("routers.support.get_connection", side_effect=[FakeConnection(product_cursor), FakeConnection(message_cursor)]):
            with self.assertRaises(HTTPException) as error:
                ask_product_question(12, MessageCreate(message="Soru"), {"id": 7, "role": "customer"})
        self.assertEqual(error.exception.status_code, 429)
        self.assertIn("P.IS_ACTIVE = TRUE", product_cursor.queries[0][0])
        self.assertIn("S.APPROVAL_STATUS = 'APPROVED'", product_cursor.queries[0][0])
        self.assertIn("S.IS_TEMPORARILY_CLOSED = FALSE", product_cursor.queries[0][0])

    def test_product_question_creates_thread_for_product_owner(self):
        product_cursor = FakeCursor(rows=[{"owner_user_id": 9}])
        message_cursor = FakeCursor(rows=[{"message_count": 0}, {"id": 14},
                                          {"id": 52, "created_at": datetime.now(timezone.utc)}])
        with patch("routers.support.get_connection", side_effect=[FakeConnection(product_cursor), FakeConnection(message_cursor)]):
            result = ask_product_question(12, MessageCreate(message="Soru"), {"id": 7, "role": "customer"})
        self.assertEqual(result, {"thread_id": 14, "message_id": 52})
        self.assertEqual(message_cursor.queries[2][1], ("product_question", 7, 9, 12))

    def test_missing_product_question_and_missing_status_thread_return_404(self):
        for operation in ("question", "status"):
            with self.subTest(operation=operation):
                cursor = FakeCursor(rows=[None])
                with patch("routers.support.get_connection", return_value=FakeConnection(cursor)):
                    with self.assertRaises(HTTPException) as error:
                        if operation == "question":
                            ask_product_question(12, MessageCreate(message="Soru"), {"id": 7, "role": "customer"})
                        else:
                            update_thread_status(14, ThreadStatusUpdate(status="open"), {"id": 2, "role": "admin"})
                self.assertEqual(error.exception.status_code, 404)
                self.assertEqual(len(cursor.queries), 1)


if __name__ == "__main__":
    unittest.main()
