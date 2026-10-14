
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@app.get("/")
def home():
    return {"message": "Merhaba CaseMarket!"}


@app.get("/api/products")
def get_products():

    db_password = os.getenv("POSTGRES_PASSWORD")

    if not db_password:
        raise RuntimeError("Veritabani sifresi bulunamadi!")

    with psycopg.connect(
        host="127.0.0.1",
        port=5433,
        dbname="casemarket_db",
        user="casemarket_user",
        password=db_password
    ) as connection:

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
