import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv



BASE_DIR=Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

def get_connection():
    db_password= os.getenv("POSTGRES_PASSWORD")

    if not db_password:
        raise RuntimeError("Veritabanı Şifresi Bulunamadı")

    return psycopg.connect(
        host="127.0.0.1",
        port=5433,
        dbname="casemarket_db",
        user="casemarket_user",
        password=db_password
    )