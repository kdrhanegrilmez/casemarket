import psycopg
from psycopg_pool import ConnectionPool

from core.config import settings


# FASTAPI ICIN ORTAK POSTGRESQL BAGLANTI HAVUZU
_db_pool = None #ilk başta bağlantı havuzumuz yok.


# VERITABANI BAGLANTI BILGILERI
def _connection_settings():
    return {
        "host": settings.database_host,
        "port": settings.database_port,
        "dbname": settings.database_name,
        "user": settings.database_user,
        "password": settings.postgres_password,
    }


# UYGULAMA BASLARKEN HAVUZU OLUSTUR
def open_db_pool():
    global _db_pool

    # Havuz zaten olusturulmussa tekrar olusturma.
    if _db_pool is not None:
        return

    pool = ConnectionPool(
        kwargs=_connection_settings(),
        # havuz boşta olsa bile en az kaç port/bağlantı boşta olmalı onu belirtiyoruz
        min_size=2,
        # Havuzun açabileceği en fazla eşzamanlı bağlantı sayısı
        max_size=10,
        # tüm bağlantılar başka işlemler tarafından kullanılıyorsa yeni gelen isteğin boşta bekleyeceği süre
        timeout=5,
        # portlar doluyken havuzda en fazla 50 istek beklet
        max_waiting=50,
        open=False,
    )

    try:
        # en az iki bağlantı hazır olana kadar bekle
        pool.open(wait=True, timeout=10)
    except Exception:
        pool.close()
        raise

    _db_pool = pool


# UYGULAMA KAPANIRKEN HAVUZU KAPAT
def close_db_pool():
    global _db_pool

    if _db_pool is not None:
        _db_pool.close()
        _db_pool = None


# ROUTER DOSYALARININ KULLANDIGI FONKSIYON
def get_connection():
    if _db_pool is not None:
        # Baglantiyi havuzdan odunc al.
        return _db_pool.connection()

    # Migration ve seed gibi FastAPI disinda
    # calisan scriptler icin normal baglanti.
    return psycopg.connect(**_connection_settings())