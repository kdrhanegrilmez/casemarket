import unittest

from main import app


class RouteCompatibilityTests(unittest.TestCase):
    def test_public_api_paths_are_preserved(self):
        schema = app.openapi()
        actual_routes = {
            (method.upper(), path)
            for path, operations in schema["paths"].items()
            for method in operations
        }
        expected_routes = {
            ("GET", "/"),
            ("GET", "/api/products"),
            ("GET", "/api/catalog/products"),
            ("GET", "/api/products/{product_id}"),
            ("POST", "/api/auth/register"),
            ("POST", "/api/auth/login"),
            ("GET", "/api/sellers/me/orders"),
            ("PATCH", "/api/sellers/me/orders/{order_id}/items/{item_id}/shipping"),
        }

        self.assertTrue(expected_routes.issubset(actual_routes))
        self.assertNotIn(("POST", "/api/products"), actual_routes)
        self.assertNotIn(("PATCH", "/api/products/{product_id}/stock"), actual_routes)


if __name__ == "__main__":
    unittest.main()
