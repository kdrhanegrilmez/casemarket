from contextlib import asynccontextmanager
import logging



from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from psycopg_pool import PoolTimeout, TooManyRequests

from database import open_db_pool, close_db_pool, get_connection

from routers import catalog, login, me, products, register, seller
from routers import seller_products, orders, account, checkout
from routers import seller_orders
from routers import admin_dashboard, admin_sellers, support
from routers import admin_store_status



# FASTAPI BASLARKEN VE KAPANIRKEN CALISAN BOLUM

def check_support_migration():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                    EXISTS (SELECT 1 FROM information_schema.columns
                            WHERE table_schema = current_schema()
                              AND table_name = 'support_threads' AND column_name = 'status'),
                    EXISTS (SELECT 1 FROM information_schema.tables
                            WHERE table_schema = current_schema()
                              AND table_name = 'support_thread_reads')"""
            )
            status_exists, reads_exists = cursor.fetchone()
    if not status_exists or not reads_exists:
        raise RuntimeError("Migration uygulanmamış: apply_support_read_status_migration.py")

@asynccontextmanager
async def lifespan(app: FastAPI):

    #Uygulama başlarken PostgreSQL havuzunu aç
    open_db_pool()

    try:
        check_support_migration()
        # Bu noktada FastAPI gelen isteklere cevap verir.
        yield
    finally:
        # Uygulama kapandiginda havuzu kapat.
        close_db_pool()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(Exception)
async def server_error_handler(request: Request, exc: Exception):
    logging.exception("Sunucu hatası: %s %s", request.method, request.url.path,
                      exc_info=(type(exc), exc, exc.__traceback__))
    return JSONResponse(status_code=500, content={"detail": "Sunucu hatası"})


# Genel Exception handler Starlette'in dış hata katmanında çalışır.
# Yanıtı CORS'un içinde oluştur ki tarayıcı 500 JSON'unu okuyabilsin.
@app.middleware("http")
async def json_server_errors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        return await server_error_handler(request, exc)

# BAGLANTI HAVUZU YOGUNSA 503 HATASI DONDUR
@app.exception_handler(PoolTimeout)
@app.exception_handler(TooManyRequests)
async def databasse_busy_handler(
        request: Request,
        exc: Exception,
):
    return JSONResponse(
        status_code=503,
        content={
            "detail":("Sunucu şu anda yoğun"
                      "Lütfen biraz sonra tekrar deneyin")
        },
        headers={"Retry-After": "5"},
    )

# FRONTEND ILE BACKEND ARASINDAKI CORS AYARLARI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173",
        "http://127.0.0.1:5173",],
    allow_credentials=False,
    allow_methods=["GET", "POST","PATCH","DELETE"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message":"Merhaba CaseMarket"}





# ROUTER BAGLANTILARI

app.include_router(products.router)
app.include_router(catalog.router)
app.include_router(register.router)
app.include_router(login.router)
app.include_router(me.router)

app.include_router(seller.router)

app.include_router(seller_products.router)
app.include_router(seller_orders.router)

app.include_router(orders.router)
app.include_router(account.router)
app.include_router(checkout.router)
app.include_router(admin_sellers.router)
app.include_router(admin_dashboard.router)
app.include_router(admin_store_status.router)
app.include_router(support.router)
