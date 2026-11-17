import unittest
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from main import app
from routers.admin_store_status import StoreClosureUpdate, update_store_closure
from routers.admin_dashboard import list_stores
from routers.catalog import get_catalog_products, get_catalog_product_detail
from tests.test_admin_commission import FakeCursor, FakeConnection


class StoreClosureTests(unittest.TestCase):
    def test_close_and_reopen_keep_seller_role_and_product_states(self):
        for closing in (True, False):
            with self.subTest(closing=closing):
                cursor = FakeCursor({"id": 12, "approval_status": "approved",
                                     "is_temporarily_closed": not closing, "closure_reason": "Önceki gerekçe"})
                connection = FakeConnection(cursor)
                with patch('routers.admin_store_status.get_connection', return_value=connection):
                    result = update_store_closure(12, StoreClosureUpdate(is_temporarily_closed=closing, reason="  İnceleme işlemi  "), {"id": 2, "role": "admin"})
                self.assertTrue(connection.committed)
                self.assertEqual(result['is_temporarily_closed'], closing)
                self.assertEqual(result['closure_reason'], 'İnceleme işlemi' if closing else None)
                self.assertIn('FOR UPDATE', cursor.queries[0][0])
                self.assertEqual(cursor.queries[1][1], (closing, 'İnceleme işlemi' if closing else None, 12))
                self.assertEqual(cursor.queries[2][1][1], 'seller.temporarily_closed' if closing else 'seller.reopened')
                self.assertFalse(any('UPDATE USERS' in sql or 'UPDATE PRODUCTS' in sql for sql, _ in cursor.queries))

    def test_non_admin_cannot_change_closure(self):
        for role in ('seller', 'customer'):
            with self.assertRaises(HTTPException) as error:
                update_store_closure(12, StoreClosureUpdate(is_temporarily_closed=True, reason='İnceleme'), {'id': 7, 'role': role})
            self.assertEqual(error.exception.status_code, 403)

    def test_missing_unapproved_and_duplicate_state_are_rejected(self):
        for store, status in ((None, 404), ({'approval_status': 'pending'}, 409),
                              ({'approval_status': 'rejected'}, 409),
                              ({'approval_status': 'approved', 'is_temporarily_closed': True}, 409)):
            cursor = FakeCursor(store)
            connection = FakeConnection(cursor)
            with patch('routers.admin_store_status.get_connection', return_value=connection):
                with self.assertRaises(HTTPException) as error:
                    update_store_closure(12, StoreClosureUpdate(is_temporarily_closed=True, reason='İnceleme'), {'id': 2, 'role': 'admin'})
            self.assertEqual(error.exception.status_code, status)
            self.assertTrue(connection.rolled_back)
            self.assertEqual(len(cursor.queries), 1)

    def test_audit_failure_rolls_back_closure(self):
        cursor = FakeCursor({'id': 12, 'approval_status': 'approved', 'is_temporarily_closed': False, 'closure_reason': None}, fail_audit=True)
        connection = FakeConnection(cursor)
        with patch('routers.admin_store_status.get_connection', return_value=connection):
            with self.assertRaises(RuntimeError):
                update_store_closure(12, StoreClosureUpdate(is_temporarily_closed=True, reason='İnceleme'), {'id': 2, 'role': 'admin'})
        self.assertTrue(connection.rolled_back)

    def test_validation_and_route(self):
        for values in ({'is_temporarily_closed': True, 'reason': '     '},
                       {'is_temporarily_closed': 'false', 'reason': 'İnceleme'},
                       {'is_temporarily_closed': True, 'reason': 'x' * 501}):
            with self.assertRaises(ValidationError):
                StoreClosureUpdate(**values)
        self.assertIn('patch', app.openapi()['paths']['/api/admin/stores/{seller_id}/temporary-closure'])

    def test_admin_list_returns_closure_fields(self):
        with patch('routers.admin_dashboard.read_page', return_value={'items': []}) as read:
            list_stores()
        self.assertIn('s.is_temporarily_closed', read.call_args.args[0])
        self.assertIn('s.closure_reason', read.call_args.args[0])

    def test_catalog_list_and_detail_exclude_closed_stores(self):
        class CatalogCursor(FakeCursor):
            def execute(self, sql, params=()):
                super().execute(sql, params)

            def fetchall(self):
                return []

        for detail in (True, False):
            cursor = CatalogCursor(None)
            with patch('routers.catalog.get_connection', return_value=FakeConnection(cursor)):
                if detail:
                    with self.assertRaises(HTTPException) as error:
                        get_catalog_product_detail(12)
                    self.assertEqual(error.exception.status_code, 404)
                else:
                    self.assertEqual(get_catalog_products(), [])
            self.assertIn('S.IS_TEMPORARILY_CLOSED = FALSE', cursor.queries[0][0])

    def test_both_order_paths_block_closed_store_before_writing(self):
        from routers.orders import create_order
        from routers.checkout import checkout_demo
        from schemas.orders import OrderCreate
        from tests.test_orders import FakeCursor as OrderCursor, FakeConnection as OrderConnection

        data = OrderCreate(items=[{'product_id': 12, 'quantity': 1}], address_id=1, payment_method_id=1)
        for checkout in (False, True):
            with self.subTest(checkout=checkout):
                rows = [('Alıcı', '5555555555', 'Ankara', 'Merkez', 'Uzun adres', None),
                        ('Visa', '1234', 12, 2099), None] if checkout else [None]
                cursor = OrderCursor(one=rows)
                connection = OrderConnection(cursor)
                target = 'routers.checkout.get_connection' if checkout else 'routers.orders.get_connection'
                with patch(target, return_value=connection):
                    with self.assertRaises(HTTPException) as error:
                        (checkout_demo if checkout else create_order)(data, {'id': 7, 'role': 'customer'})
                self.assertEqual(error.exception.status_code, 404)
                product_sql = next(sql for sql, _ in cursor.queries if 'FROM PRODUCTS AS P' in sql)
                self.assertIn('S.IS_TEMPORARILY_CLOSED = FALSE', product_sql)
                self.assertIn('FOR SHARE OF S', product_sql)
                self.assertFalse(any('INSERT INTO ORDERS' in sql for sql, _ in cursor.queries))
                self.assertTrue(connection.rolled_back)
