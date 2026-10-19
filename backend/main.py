from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import login, products, register


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "Merhaba CaseMarket!"}


app.include_router(products.router)
app.include_router(register.router)
app.include_router(login.router)
