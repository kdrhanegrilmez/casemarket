import unittest
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from core.dependencies import require_admin
from main import app
from routers.admin_sellers import SellerAccessRevocation, SellerApplicationReview, list_seller_applications, review_seller_application, revoke_seller_access
from routers.seller import create_seller
from schemas.sellers import SellerCreate


class FakeCursor:
    def __init__(self, rows, many=()):
        self.rows = iter(rows)
        self.many = many
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

    def fetchall(self):
        return self.many


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

    def test_revocation_changes_role_and_store_status_with_audit(self):
        cursor = FakeCursor([(12, 7, "Mağaza", "approved", "seller"), (7,)])
        connection = FakeConnection(cursor)
        with patch("routers.admin_sellers.get_connection", return_value=connection):
            result = revoke_seller_access(12, SellerAccessRevocation(reason="  Kural ihlali  "), {"id": 2, "role": "admin"})
        self.assertTrue(connection.committed)
        self.assertEqual(result["user_role"], "customer")
        self.assertEqual(result["approval_status"], "pending")
        self.assertIn("FOR UPDATE OF S, U", cursor.queries[0][0])
        self.assertIn("SET ROLE = 'CUSTOMER'", cursor.queries[1][0])
        self.assertEqual(cursor.queries[2][1], (2, "Kural ihlali", 12))
        self.assertEqual(cursor.queries[3][1][1], "seller.access_revoked")
        self.assertEqual(cursor.queries[3][1][4].obj, {"approval_status": "approved", "user_role": "seller"})

    def test_revocation_requires_admin_and_reason(self):
        with self.assertRaises(ValidationError):
            SellerAccessRevocation(reason="     ")
        for role in ("customer", "seller"):
            with self.assertRaises(HTTPException) as error:
                revoke_seller_access(12, SellerAccessRevocation(reason="Kural ihlali"), {"id": 7, "role": role})
            self.assertEqual(error.exception.status_code, 403)

    def test_revocation_rejects_missing_or_ineligible_store(self):
        for row, code in ((None, 404), ((12, 7, "Mağaza", "pending", "customer"), 409),
                          ((12, 7, "Mağaza", "approved", "admin"), 409)):
            cursor = FakeCursor([row])
            connection = FakeConnection(cursor)
            with patch("routers.admin_sellers.get_connection", return_value=connection):
                with self.assertRaises(HTTPException) as error:
                    revoke_seller_access(12, SellerAccessRevocation(reason="Kural ihlali"), {"id": 2, "role": "admin"})
            self.assertEqual(error.exception.status_code, code)
            self.assertTrue(connection.rolled_back)
            self.assertEqual(len(cursor.queries), 1)

    def test_revocation_audit_failure_rolls_back_role_and_store(self):
        class AuditFailureCursor(FakeCursor):
            def execute(self, sql, params):
                super().execute(sql, params)
                if "INSERT INTO ADMIN_AUDIT_LOGS" in self.queries[-1][0]:
                    raise RuntimeError("audit failed")
        cursor = AuditFailureCursor([(12, 7, "Mağaza", "approved", "seller"), (7,)])
        connection = FakeConnection(cursor)
        with patch("routers.admin_sellers.get_connection", return_value=connection):
            with self.assertRaises(RuntimeError):
                revoke_seller_access(12, SellerAccessRevocation(reason="Kural ihlali"), {"id": 2, "role": "admin"})
        self.assertTrue(connection.rolled_back)

    def test_revocation_route_is_registered(self):
        self.assertIn("patch", app.openapi()["paths"]["/api/admin/seller-application/{seller_id}/revoke"])

    def test_application_list_includes_revocation_reason(self):
        cursor = FakeCursor([], many=[(12, "Mağaza", None, "pending", None, 7, "Satıcı", "s@example.com", "2026-11-17", "Kural ihlali")])
        with patch("routers.admin_sellers.get_connection", return_value=FakeConnection(cursor)):
            result = list_seller_applications("pending", {"id": 2, "role": "admin"})
        self.assertEqual(result[0]["review_reason"], "Kural ihlali")
        self.assertEqual(result[0]["reviewed_at"], "2026-11-17")


if __name__ == "__main__":
    unittest.main()
