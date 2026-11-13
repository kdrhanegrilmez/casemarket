import unittest
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from core.dependencies import require_admin
from main import app
from routers.admin_sellers import SellerApplicationReview, review_seller_application
from routers.seller import create_seller
from schemas.sellers import SellerCreate


class FakeCursor:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params):
        normalized = " ".join(sql.upper().split())
        self.queries.append((normalized, params))

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

    def cursor(self):
        return self.fake_cursor


class SellerApprovalTests(unittest.TestCase):
    def test_new_store_stays_pending_without_seller_role(self):
        cursor = FakeCursor([("customer",), (12, "Mağaza", None, "pending")])
        with patch("routers.seller.get_connection", return_value=FakeConnection(cursor)):
            result = create_seller(SellerCreate(store_name="Mağaza"), {"id": 7, "role": "customer"})

        self.assertEqual(result["approval_status"], "pending")
        self.assertFalse(any(sql.startswith("UPDATE USERS") for sql, _ in cursor.queries))

    def test_approved_decision_is_a_valid_model(self):
        decision = SellerApplicationReview.model_validate({"decision": "approved"})
        self.assertEqual(decision.decision, "approved")

    def test_rejection_needs_reason(self):
        with self.assertRaises(ValidationError):
            SellerApplicationReview.model_validate({"decision": "rejected", "reason": "  "})

    def test_review_uses_patch(self):
        path = app.openapi()["paths"]["/api/admin/seller-application/{seller_id}/review"]
        self.assertIn("patch", path)
        self.assertNotIn("get", path)

    def test_approval_changes_role_and_writes_audit_in_one_transaction(self):
        cursor = FakeCursor([(12, 7, "Mağaza", "pending", "customer"), (7,)])
        connection = FakeConnection(cursor)
        with patch("routers.admin_sellers.get_connection", return_value=connection):
            result = review_seller_application(
                12, SellerApplicationReview(decision="approved"), {"id": 2, "role": "admin"}
            )

        self.assertTrue(connection.committed)
        self.assertEqual(result["user_role"], "seller")
        self.assertEqual(len(cursor.queries), 4)
        self.assertIn("REVIEWED_AT = NOW(),", cursor.queries[1][0])
        self.assertIn("UPDATE USERS SET ROLE = 'SELLER'", cursor.queries[2][0])
        self.assertEqual(cursor.queries[2][1], (7,))
        self.assertIn("INSERT INTO ADMIN_AUDIT_LOGS", cursor.queries[3][0])

    def test_rejection_keeps_customer_role(self):
        cursor = FakeCursor([(12, 7, "Mağaza", "pending", "customer")])
        with patch("routers.admin_sellers.get_connection", return_value=FakeConnection(cursor)):
            result = review_seller_application(
                12,
                SellerApplicationReview(decision="rejected", reason="Eksik bilgi"),
                {"id": 2, "role": "admin"},
            )

        self.assertEqual(result["user_role"], "customer")
        self.assertFalse(any(sql.startswith("UPDATE USERS") for sql, _ in cursor.queries))

    def test_non_admin_is_forbidden(self):
        with self.assertRaises(HTTPException) as error:
            require_admin({"id": 7, "role": "customer"})
        self.assertEqual(error.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
