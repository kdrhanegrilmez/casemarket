import asyncio
import json
import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from psycopg_pool import PoolTimeout

from main import app, check_support_migration, lifespan


class StartupSchemaTests(unittest.IsolatedAsyncioTestCase):
    def test_support_schema_requires_both_status_and_reads(self):
        for status, reads in ((True, True), (False, True), (True, False), (False, False)):
            with self.subTest(status=status, reads=reads):
                connection = MagicMock()
                cursor = connection.__enter__.return_value.cursor.return_value.__enter__.return_value
                cursor.fetchone.return_value = (status, reads)
                with patch('main.get_connection', return_value=connection):
                    if status and reads:
                        check_support_migration()
                    else:
                        with self.assertRaisesRegex(RuntimeError, 'Migration uygulanmamış: apply_support_read_status_migration.py'):
                            check_support_migration()

    async def test_startup_failure_closes_pool_without_serving(self):
        with patch('main.open_db_pool') as opened, patch('main.close_db_pool') as closed, patch(
            'main.check_support_migration', side_effect=RuntimeError('Migration uygulanmamış')
        ):
            with self.assertRaisesRegex(RuntimeError, 'Migration uygulanmamış'):
                async with lifespan(app):
                    self.fail('Eksik migration ile uygulama başladı.')
            opened.assert_called_once()
            closed.assert_called_once()

    async def test_valid_startup_serves_and_closes_pool(self):
        with patch('main.open_db_pool') as opened, patch('main.close_db_pool') as closed, patch('main.check_support_migration') as checked:
            async with lifespan(app):
                opened.assert_called_once()
                checked.assert_called_once()
                closed.assert_not_called()
            closed.assert_called_once()


class ErrorResponseTests(unittest.IsolatedAsyncioTestCase):
    async def request_failure(self, exception, origin='http://localhost:5173'):
        async def fail():
            raise exception

        app.add_api_route('/__test_server_error', fail, methods=['GET'])
        route = app.router.routes[-1]
        sent = []
        delivered = False

        async def receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': b'', 'more_body': False}
            await asyncio.Event().wait()

        async def send(message):
            sent.append(message)

        try:
            await app({
                'type': 'http', 'asgi': {'version': '3.0', 'spec_version': '2.0'},
                'http_version': '1.1', 'method': 'GET', 'scheme': 'http',
                'path': '/__test_server_error', 'raw_path': b'/__test_server_error',
                'query_string': b'', 'root_path': '', 'headers': [(b'origin', origin.encode())],
                'server': ('testserver', 80), 'client': ('127.0.0.1', 1234),
            }, receive, send)
        finally:
            app.router.routes.remove(route)
        start = next(item for item in sent if item['type'] == 'http.response.start')
        body = b''.join(item.get('body', b'') for item in sent if item['type'] == 'http.response.body')
        return start['status'], dict(start['headers']), json.loads(body)

    async def test_unhandled_error_returns_json_cors_and_logs_traceback(self):
        failure = RuntimeError('Gizli veritabanı ayrıntısı')
        with patch('main.logging.exception') as logged:
            status, headers, body = await self.request_failure(failure)
        self.assertEqual(status, 500)
        self.assertEqual(body, {'detail': 'Sunucu hatası'})
        self.assertEqual(headers[b'access-control-allow-origin'], b'http://localhost:5173')
        self.assertIn(b'application/json', headers[b'content-type'])
        logged.assert_called_once()
        self.assertIs(logged.call_args.kwargs['exc_info'][1], failure)
        self.assertIsNotNone(logged.call_args.kwargs['exc_info'][2])

    async def test_http_errors_preserve_status_and_detail(self):
        with patch('main.logging.exception') as logged:
            status, headers, body = await self.request_failure(HTTPException(404, 'Bulunamadı'))
        self.assertEqual((status, body), (404, {'detail': 'Bulunamadı'}))
        self.assertIn(b'access-control-allow-origin', headers)
        logged.assert_not_called()

    async def test_pool_exhaustion_remains_503_with_retry_header(self):
        status, headers, _ = await self.request_failure(PoolTimeout('pool busy'))
        self.assertEqual(status, 503)
        self.assertEqual(headers[b'retry-after'], b'5')

    async def test_untrusted_origin_does_not_receive_cors_permission(self):
        with patch('main.logging.exception'):
            status, headers, _ = await self.request_failure(RuntimeError('boom'), 'https://untrusted.example')
        self.assertEqual(status, 500)
        self.assertNotIn(b'access-control-allow-origin', headers)
