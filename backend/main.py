from contextlib import asynccontextmanager



from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from psycopg_pool import PoolTimeout, TooManyRequests

from database import open_db_pool, close_db_pool

from routers import catalog, login, me, products, register, seller
from routers import seller_products, orders, account, checkout



# FASTAPI BASLARKEN VE KAPANIRKEN CALISAN BOLUM

@asynccontextmanager
async def lifespan(app: FastAPI):

    #Uygulama başlarken PostgreSQL havuzunu aç
    open_db_pool()

    try:
        # Bu noktada FastAPI gelen isteklere cevap verir.
        yield
    finally:
        # Uygulama kapandiginda havuzu kapat.
        close_db_pool()


app = FastAPI(lifespan=lifespan)

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
        headers={"Retry-After": 5},
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

app.include_router(orders.router)
app.include_router(account.router)
app.include_router(checkout.router)
