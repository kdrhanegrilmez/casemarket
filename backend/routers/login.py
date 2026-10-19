from fastapi import APIRouter, HTTPException, status

from core.security import create_access_token, verify_password
from database import get_connection
from schemas.auth import TokenResponse, UserLogin


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="E-posta veya parola hatali.",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/login", response_model=TokenResponse)
def login_user(data: UserLogin):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, password_hash
                FROM users
                WHERE email = %s
                """,
                (str(data.email).lower(),),
            )
            user = cursor.fetchone()

    if user is None or not verify_password(data.password, user[1]):
        raise _invalid_credentials()

    return TokenResponse(access_token=create_access_token(user[0]))
