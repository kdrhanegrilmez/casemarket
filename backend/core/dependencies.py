import jwt

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.config import settings
from database import get_connection

bearer_scheme = HTTPBearer(auto_error=False)


def unauthorized_error():
    return HTTPException(
        status_code=401,
        detail="Gecersiz veya suresi dolmus oturum.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    # Token gonderilmediyse girisi reddet
    if credentials is None:
        raise unauthorized_error()

    # JWT imzasini ve suresini dogrula
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp"]},
        )

        subject = payload["sub"]

        if (
                not isinstance(subject, str)
                or not subject.isascii()
                or not subject.isdigit()
        ):
            raise ValueError("Gecersiz kullanici ID")

        user_id = int(subject)

        if user_id <= 0:
            raise ValueError("Gecersiz kullanici ID")

    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
        raise unauthorized_error() from None

    # Kullanici hala veritabaninda var mi?
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, full_name, email, role
                FROM users
                WHERE id = %s

                """,
                (user_id,),
            )
            user = cursor.fetchone()

    if user is None:
        raise unauthorized_error()

    return {
        "id": user[0],
        "full_name": user[1],
        "email": user[2],
        "role": user[3],
    }
