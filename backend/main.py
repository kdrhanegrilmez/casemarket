

import os
from datetime import datetime, timedelta, timezone

import jwt
from argon2.exceptions import VerificationError, InvalidHashError

from decimal import Decimal


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from argon2 import PasswordHasher
from psycopg.errors import UniqueViolation
#iki farklı port arasında tarayıcada veri paylaşımı güveliğini sağlar
from pydantic import BaseModel, Field, EmailStr
from pygments.lexers import data

from database import get_connection
#database.py içerisindeki bağlantı fonksiyonumuzu kullanmamızı sağlıyor.



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    #REACT'ın çalıştığı adreslere izin verir.
    allow_credentials=False,
    #Şimdilik tarayıcı kimlik bilgilerinin gönderilmesine izin vermez
    allow_methods=["GET"],
    #React'ın okuma isteklerine izin verir.
    allow_headers=["*"],
    #İstekte kullanılabilecek HTTP başlıklarına izin verir
)



class ProductCreate(BaseModel):
    name:str = Field(min_length=3,max_length=100)
    price:Decimal =Field(gt=0,max_digits=10, decimal_places=2)
    #fiyat toplam en fazla 10 basamak ve decimal_places=2 ile virgülden sonra en fazla 2 bsamak alıyoruz
    #gt=0, burada fiyatın 0 dan büyük olmasını istiyoruz ve basamaklı fiyatlara izin veriyoruz
    stock:int =Field(ge=0)
    seller_id:int = Field(gt=0)



class ProductStockUpdate(BaseModel):
    stock:int =Field(ge=0)



@app.get("/")
def home():
    return {"message": "Merhaba CaseMarket!"}


@app.get("/api/products")
def get_products():

    with get_connection() as connection:

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    p.id,
                    p.name,
                    p.price,
                    p.stock,
                    s.store_name
                FROM practice_products AS p
                LEFT JOIN practice_seller AS s
                    ON p.seller_id = s.id
                ORDER BY p.id;
            """)

            rows = cursor.fetchall()

    products = []

    for row in rows:
        product = {
            "id": row[0],
            "name": row[1],
            "price": str(row[2]),
            "stock": row[3],
            "seller": row[4]
        }

        products.append(product)

    return products




@app.get("/api/products/{product_id}")
def get_product(product_id: int):

    with get_connection() as connection:

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    p.id,
                    p.name,
                    p.price,
                    p.stock,
                    s.store_name
                FROM practice_products AS p
                LEFT JOIN practice_seller AS s
                    ON p.seller_id = s.id
                WHERE p.id = %s;
            """, (product_id,))

            row = cursor.fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Urun bulunamadi!"
        )

    product = {
        "id": row[0],
        "name": row[1],
        "price": str(row[2]),
        "stock": row[3],
        "seller": row[4]
    }

    return product


@app.post("/api/products", status_code=201)
def create_product(product: ProductCreate):

    with get_connection() as connection:

        with connection.cursor() as cursor:

            #önce satıcı gerçekten bizim sistemimizde bir satıcı mı.
            #yani id'si bize kayıtlı mı, db de öyle bir kullanıcı var mı check et

            cursor.execute(
                "SELECT 1 FROM practice_seller WHERE id=%s ",
                (product.seller_id,)
            )
            seller_exist =cursor.fetchone()
            if seller_exist is None:
                raise HTTPException(
                    status_code=400,
                    detail="Kayitli satici bulunamadi!"
                )

            cursor.execute("""
                INSERT INTO practice_products
                    (name, price, stock, seller_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """, (
                product.name,
                product.price,
                product.stock,
                product.seller_id
            ))

            new_product_id = cursor.fetchone()[0]

    return {
        "message": "Urun basariyla kaydedildi!",
        "id": new_product_id,
        "name": product.name,
        "price": str(product.price),
        "stock": product.stock,
        "seller_id": product.seller_id
    }







@app.patch("/api/products/{product_id}/stock")
def update_product_stock(
    product_id: int,
    update: ProductStockUpdate
):

    with get_connection() as connection:

        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE practice_products
                SET stock = %s
                WHERE id = %s
                RETURNING id, name, stock;
            """, (update.stock, product_id))

            row = cursor.fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Urun bulunamadi!"
        )

    return {
        "id": row[0],
        "name": row[1],
        "stock": row[2],
        "message": "Stok basariyla guncellendi!"
    }



# Kullanıcı kaydı

password_hasher = PasswordHasher()


class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


@app.post("/api/auth/register", status_code=201)
def register_user(data: UserRegister):
    full_name = data.full_name.strip()

    if len(full_name) < 2:
        raise HTTPException(
            status_code=422,
            detail="Ad en az 2 karakter olmali."
        )

    password_hash = password_hasher.hash(data.password)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users
                        (full_name, email, password_hash, role)
                    VALUES (%s, %s, %s, 'customer')
                    RETURNING id, full_name, email, role
                    """,
                    (
                        full_name,
                        str(data.email).lower(),
                        password_hash
                    )
                )

                user = cur.fetchone()

    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Bu e-posta adresi zaten kayitli."
        ) from None

    return {
        "id": user[0],
        "full_name": user[1],
        "email": user[2],
        "role": user[3]
    }

