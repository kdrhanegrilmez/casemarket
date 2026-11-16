import unittest
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from routers.admin_dashboard import CommissionRateUpdate, update_store_commission


class FakeCursor:
    def __init__(self, store, fail_audit=False):
        self.store = store
        self.fail_audit = fail_audit
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params):
        normalized = " ".join(sql.upper().split())
        self.queries.append((normalized, params))
        if self.fail_audit and normalized.startswith("INSERT INTO ADMIN_AUDIT_LOGS"):
            raise RuntimeError("audit failed")

    def fetchone(self):
        return self.store


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


class AdminCommissionTests(unittest.TestCase):
    def test_rate_validation(self):
        self.assertEqual(CommissionRateUpdate(commission_rate_percent="10.25").commission_rate_percent, Decimal("10.25"))
        for rate in ("-1", "100.01", "1.001"):
            with self.subTest(rate=rate), self.assertRaises(ValidationError):
                CommissionRateUpdate(commission_rate_percent=rate)

    def test_update_and_audit_share_transaction(self):
        cursor = FakeCursor({"id": 12, "approval_status": "approved", "commission_rate_percent": None})
        connection = FakeConnection(cursor)
        with patch("routers.admin_dashboard.get_connection", return_value=connection):
            result = update_store_commission(12, CommissionRateUpdate(commission_rate_percent="12.50"), {"id": 2})

        self.assertTrue(connection.committed)
        self.assertEqual(result["commission_rate_percent"], "12.50")
        self.assertEqual(len(cursor.queries), 3)
        self.assertIn("UPDATE SELLERS SET COMMISSION_RATE_PERCENT", cursor.queries[1][0])
        self.assertIn("INSERT INTO ADMIN_AUDIT_LOGS", cursor.queries[2][0])
        self.assertEqual(cursor.queries[2][1][:4], (2, "seller.commission_updated", "seller", 12))

    def test_pending_store_cannot_receive_rate(self):
        cursor = FakeCursor({"id": 12, "approval_status": "pending", "commission_rate_percent": None})
        connection = FakeConnection(cursor)
        with patch("routers.admin_dashboard.get_connection", return_value=connection):
            with self.assertRaises(HTTPException) as error:
                update_store_commission(12, CommissionRateUpdate(commission_rate_percent="10"), {"id": 2})

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(len(cursor.queries), 1)

    def test_audit_failure_rolls_back_rate_change(self):
        cursor = FakeCursor({"id": 12, "approval_status": "approved", "commission_rate_percent": None}, fail_audit=True)
        connection = FakeConnection(cursor)
        with patch("routers.admin_dashboard.get_connection", return_value=connection):
            with self.assertRaises(RuntimeError):
                update_store_commission(12, CommissionRateUpdate(commission_rate_percent="10"), {"id": 2})

        self.assertTrue(connection.rolled_back)


if __name__ == "__main__":
    unittest.main()
