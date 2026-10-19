
from fastapi import APIRouter, Depends, HTTPException
from psycopg.errors import UniqueViolation

from core.dependencies import get_current_user
from database import get_connection
from schemas.sellers import SellerCreate


router = APIRouter(prefix="/api/sellers", tags=["sellers"])


@router.post("", status_code=201)
def create_seller(
    data: SellerCreate,
    current_user: dict = Depends(get_current_user),
):
    # Yalnizca musteriler yeni magaza acabilir.
    if current_user["role"] != "customer":
        raise HTTPException(
            status_code=409,
            detail="Bu hesap yeni bir magaza acamaz.",
        )

    store_name = data.store_name.strip()

    if len(store_name) < 3:
        raise HTTPException(
            status_code=422,
            detail="Magaza adi en az 3 karakter olmali.",
        )

    description = (
        data.description.strip()
        if data.description is not None
        else None
    )

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                # Kullaniciyi satici rolune gecir.
                cursor.execute(
                    """
                    UPDATE users
                    SET role = 'seller'
                    WHERE id = %s AND role = 'customer'
                    RETURNING id
                    """,
                    (current_user["id"],),
                )

                if cursor.fetchone() is None:
                    raise HTTPException(
                        status_code=409,
                        detail="Bu hesap yeni bir magaza acamaz.",
                    )

                # Magazayi giris yapan kullaniciya bagla.
                cursor.execute(
                    """
                    INSERT INTO sellers
                        (owner_user_id, store_name, description)
                    VALUES (%s, %s, %s)
                    RETURNING id, store_name, description
                    """,
                    (
                        current_user["id"],
                        store_name,
                        description,
                    ),
                )

                seller = cursor.fetchone()

    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Bu kullaniciya ait magaza zaten var.",
        ) from None

    return {
        "id": seller[0],
        "owner_user_id": current_user["id"],
        "store_name": seller[1],
        "description": seller[2],
    }


@router.get("/me")
def get_my_store(
        current_user: dict=Depends(get_current_user),
):
    #Sadece satıcı rolündeki kullanıcılara erişmeliyiz
    if current_user["role"] != "seller":
        raise HTTPException(
                status_code=403,
                detail="Bu işlem için satıcı hesabı gerekir."
        )
    #Mağzaya giriş yapan kullanıcıya göre bulma:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, owner_user_id, store_name, description
                FROM sellers
                    WHERE owner_user_id = %s
                """,
                (current_user["id"],),
            )

            store=cursor.fetchone()
    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Mağza bulunamadı"
        )

    return{
        "id": store[0],
        "owner_user_id": store[1],
        "store_name": store[2],
        "description": store[3],
    }