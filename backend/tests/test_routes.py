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
            ("POST", "/api/products"),
            ("PATCH", "/api/products/{product_id}/stock"),
            ("POST", "/api/auth/register"),
            ("POST", "/api/auth/login"),
        }

        self.assertTrue(expected_routes.issubset(actual_routes))


if __name__ == "__main__":
    unittest.main()
