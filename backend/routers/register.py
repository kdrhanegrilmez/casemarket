from fastapi import APIRouter, HTTPException
from psycopg.errors import UniqueViolation

from core.security import hash_password
from database import get_connection
from schemas.auth import UserRegister


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register_user(data: UserRegister):
    full_name = data.full_name.strip()
    if len(full_name) < 2:
        raise HTTPException(
            status_code=422,
            detail="Ad en az 2 karakter olmali.",
        )

    password_hash = hash_password(data.password)

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users
                        (full_name, email, password_hash, role)
                    VALUES (%s, %s, %s, 'customer')
                    RETURNING id, full_name, email, role
                    """,
                    (full_name, str(data.email).lower(), password_hash),
                )
                user = cursor.fetchone()
    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Bu e-posta adresi zaten kayitli.",
        ) from None

    return {
        "id": user[0],
        "full_name": user[1],
        "email": user[2],
        "role": user[3],
    }
