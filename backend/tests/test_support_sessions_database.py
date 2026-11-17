"""İsteğe bağlı gerçek PostgreSQL + ASGI testleri; tüm test verileri rollback edilir.

CASEMARKET_DB_TESTS=1 python -m unittest tests.test_support_sessions_database -v
"""
import asyncio
from contextlib import contextmanager
import json
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from core.dependencies import get_current_user
from database import get_connection
from main import app


@unittest.skipUnless(os.environ.get('CASEMARKET_DB_TESTS') == '1', 'Gerçek PostgreSQL testi isteğe bağlıdır.')
class SupportSessionsDatabaseTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.connection = get_connection()
        self.addCleanup(self.connection.close)
        self.addCleanup(self.connection.rollback)
        self.users = {}
        with self.connection.cursor() as cursor:
            for role in ('customer', 'seller', 'admin', 'stranger'):
                actual_role = 'customer' if role == 'stranger' else role
                cursor.execute(
                    "INSERT INTO users (full_name,email,password_hash,role) VALUES (%s,%s,%s,%s) RETURNING id",
                    (f'Test {role}', f'{uuid4().hex}@session-test.invalid', 'unused-test-hash', actual_role),
                )
                self.users[role] = {'id': cursor.fetchone()[0], 'role': actual_role}
            cursor.execute("INSERT INTO sellers (owner_user_id,store_name,approval_status) VALUES (%s,%s,'approved') RETURNING id",
                           (self.users['seller']['id'], 'Görüşme Test Mağazası'))
            seller_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO products (seller_id,name,price,stock) VALUES (%s,%s,10,10) RETURNING id",
                           (seller_id, 'Görüşme Test Ürünü'))
            self.product_id = cursor.fetchone()[0]

        @contextmanager
        def connection_scope():
            # Gerçek endpoint transaction'ını dış test transaction'ı içinde savepoint ile taklit et.
            with self.connection.transaction():
                yield self.connection

        self.connection_patch = patch('routers.support.get_connection', side_effect=connection_scope)
        self.connection_patch.start()
        self.addCleanup(self.connection_patch.stop)
        previous = app.dependency_overrides.copy()
        self.addCleanup(lambda: (app.dependency_overrides.clear(), app.dependency_overrides.update(previous)))

    async def request(self, role, method, path, body=None):
        app.dependency_overrides[get_current_user] = lambda: self.users[role]
        data = json.dumps(body).encode() if body is not None else b''
        sent = []
        delivered = False

        async def receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': data, 'more_body': False}
            await asyncio.Event().wait()

        async def send(message):
            sent.append(message)

        route, _, query = path.partition('?')
        await app({
            'type': 'http', 'asgi': {'version': '3.0', 'spec_version': '2.0'},
            'http_version': '1.1', 'method': method, 'scheme': 'http',
            'path': route, 'raw_path': route.encode(), 'query_string': query.encode(), 'root_path': '',
            'headers': [(b'content-type', b'application/json'), (b'origin', b'http://localhost:5173')],
            'server': ('testserver', 80), 'client': ('127.0.0.1', 1234),
        }, receive, send)
        start = next(message for message in sent if message['type'] == 'http.response.start')
        response = json.loads(b''.join(message.get('body', b'') for message in sent if message['type'] == 'http.response.body'))
        self.assertEqual(dict(start['headers'])[b'access-control-allow-origin'], b'http://localhost:5173')
        return start['status'], response

    async def test_customer_and_seller_can_start_another_support_session(self):
        for role in ('customer', 'seller'):
            code, first = await self.request(role, 'POST', f'/api/support/{role}', {'message': 'İlk talep'})
            self.assertEqual(code, 201)
            first_id = first['thread_id']
            code, _ = await self.request('admin', 'PATCH', f'/api/support/threads/{first_id}/status', {'status': 'closed'})
            self.assertEqual(code, 200)
            code, _ = await self.request(role, 'POST', f'/api/support/threads/{first_id}/messages', {'message': 'Eski görüşmeye gönderme'})
            self.assertEqual(code, 409)
            code, second = await self.request(role, 'POST', f'/api/support/{role}', {'message': 'Yeni talep'})
            self.assertEqual(code, 201)
            self.assertNotEqual(first_id, second['thread_id'])
            code, detail = await self.request(role, 'GET', f'/api/support/threads/{first_id}')
            self.assertEqual(code, 200)
            self.assertEqual(detail['thread']['status'], 'closed')
            self.assertEqual([message['body'] for message in detail['messages']], ['İlk talep'])
            self.assertNotIn('seller_email', detail['thread'])
            # Yeni açık görüşme varken eskiyi açmak benzersiz indeksle engellenir.
            code, _ = await self.request('admin', 'PATCH', f'/api/support/threads/{first_id}/status', {'status': 'open'})
            self.assertEqual(code, 409)
            code, reused = await self.request(role, 'POST', f'/api/support/{role}', {'message': 'Yeni talebin devamı'})
            self.assertEqual(code, 201)
            self.assertEqual(reused['thread_id'], second['thread_id'])

    async def test_question_can_end_and_restart_with_history_preserved(self):
        path = f'/api/support/products/{self.product_id}/question'
        for closer in ('customer', 'seller'):
            code, first = await self.request('customer', 'POST', path, {'message': 'Ürün sorusu'})
            self.assertEqual(code, 201)
            thread_id = first['thread_id']
            code, _ = await self.request('stranger', 'PATCH', f'/api/support/threads/{thread_id}/status', {'status': 'closed'})
            self.assertEqual(code, 404)
            code, _ = await self.request(closer, 'PATCH', f'/api/support/threads/{thread_id}/status', {'status': 'closed'})
            self.assertEqual(code, 200)
            code, _ = await self.request(closer, 'POST', f'/api/support/threads/{thread_id}/messages', {'message': 'Gönderilemez'})
            self.assertEqual(code, 409)
            code, _ = await self.request(closer, 'PATCH', f'/api/support/threads/{thread_id}/status', {'status': 'open'})
            self.assertEqual(code, 403)
        code, new = await self.request('customer', 'POST', path, {'message': 'Yeni ürün sorusu'})
        self.assertEqual(code, 201)
        code, closed = await self.request('customer', 'GET', '/api/support/my/threads?channel=questions&status=closed')
        self.assertEqual(code, 200)
        self.assertEqual(len(closed), 2)
        self.assertNotIn(new['thread_id'], [item['id'] for item in closed])

    async def test_unread_ownership_and_read_updates_with_real_sql(self):
        code, created = await self.request('customer', 'POST', '/api/support/customer', {'message': 'Yardım'})
        self.assertEqual(code, 201)
        thread_id = created['thread_id']
        code, listing = await self.request('admin', 'GET', '/api/support/admin/threads?channel=customer')
        self.assertEqual(code, 200)
        self.assertEqual(next(item['unread_count'] for item in listing if item['id'] == thread_id), 1)
        code, _ = await self.request('admin', 'POST', f'/api/support/threads/{thread_id}/messages', {'message': 'Admin yanıtı'})
        self.assertEqual(code, 201)
        _, count = await self.request('customer', 'GET', '/api/support/my/unread-count')
        self.assertEqual(count['unread_count'], 1)
        _, detail = await self.request('customer', 'GET', f'/api/support/threads/{thread_id}')
        self.assertEqual(detail['messages'][-1]['sender_name'], 'Admin')
        _, count = await self.request('customer', 'GET', '/api/support/my/unread-count')
        self.assertEqual(count['unread_count'], 0)
        code, _ = await self.request('stranger', 'GET', f'/api/support/threads/{thread_id}')
        self.assertEqual(code, 404)
