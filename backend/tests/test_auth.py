import os
import time
import unittest
from unittest.mock import patch

os.environ.setdefault(
    "JWT_SECRET_KEY",
    "x" * 32,
)

import jwt
from fastapi import HTTPException
from psycopg.errors import UniqueViolation
from pydantic import ValidationError

from core.config import settings
from core.security import hash_password
from routers.login import login_user
from routers.register import register_user
from schemas.auth import UserLogin, UserRegister


class FakeCursor:
    def __init__(self, row=None, execute_error=None):
        self.row = row
        self.execute_error = execute_error

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, parameters):
        if self.execute_error:
            raise self.execute_error

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, row=None, execute_error=None):
        self.fake_cursor = FakeCursor(row, execute_error)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def cursor(self):
        return self.fake_cursor


class AuthEndpointTests(unittest.TestCase):
    @patch("routers.register.get_connection")
    def test_register_creates_customer(self, get_connection):
        get_connection.return_value = FakeConnection(
            row=(1, "Ada Lovelace", "ada@example.com", "customer")
        )
        data = UserRegister(
            full_name="Ada Lovelace",
            email="ADA@example.com",
            password="strong-password",
        )

        response = register_user(data)

        self.assertEqual(response["role"], "customer")
        self.assertNotIn("password", response)

    def test_register_rejects_role_from_request(self):
        with self.assertRaises(ValidationError):
            UserRegister.model_validate(
                {
                    "full_name": "Ada Lovelace",
                    "email": "ada@example.com",
                    "password": "strong-password",
                    "role": "admin",
                }
            )

    @patch("routers.register.get_connection")
    def test_register_returns_conflict_for_duplicate_email(self, get_connection):
        get_connection.return_value = FakeConnection(
            execute_error=UniqueViolation("duplicate email")
        )
        data = UserRegister(
            full_name="Ada Lovelace",
            email="ada@example.com",
            password="strong-password",
        )

        with self.assertRaises(HTTPException) as caught:
            register_user(data)

        self.assertEqual(caught.exception.status_code, 409)

    @patch("routers.login.get_connection")
    def test_login_returns_two_hour_bearer_token(self, get_connection):
        get_connection.return_value = FakeConnection(
            row=(42, hash_password("strong-password"))
        )
        data = UserLogin(
            email="ada@example.com",
            password="strong-password",
        )

        response = login_user(data)
        payload = jwt.decode(
            response.access_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        self.assertEqual(response.token_type, "bearer")
        self.assertEqual(payload["sub"], "42")
        self.assertGreaterEqual(payload["exp"] - int(time.time()), 7195)
        self.assertLessEqual(payload["exp"] - int(time.time()), 7200)

    @patch("routers.login.get_connection")
    def test_login_rejects_wrong_password(self, get_connection):
        get_connection.return_value = FakeConnection(
            row=(42, hash_password("correct-password"))
        )
        data = UserLogin(
            email="ada@example.com",
            password="wrong-password",
        )

        with self.assertRaises(HTTPException) as caught:
            login_user(data)

        self.assertEqual(caught.exception.status_code, 401)

    @patch("routers.login.get_connection")
    def test_login_rejects_unknown_email(self, get_connection):
        get_connection.return_value = FakeConnection(row=None)
        data = UserLogin(
            email="unknown@example.com",
            password="strong-password",
        )

        with self.assertRaises(HTTPException) as caught:
            login_user(data)

        self.assertEqual(caught.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
