import psycopg
from core.config import settings


def get_connection():
    return psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.postgres_password,
    )
