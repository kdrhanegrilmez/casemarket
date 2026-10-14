
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
## db_test.py dosyasinin bulundugu klasorden iki ust dizine cikar.

load_dotenv(BASE_DIR / ".env")

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

        products = cursor.fetchall()

        for product in products:
            print(product)

        #fetchone ile sorgudan dönen ilk satırı alırız, hepsi için fetchall kullanabiliriz.
