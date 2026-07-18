from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vstitchapi.bestSellerApi import best_seller_router
from vstitchapi.categoryapi import category_router
from vstitchapi.loginapi import login_router
from vstitchapi.orderapi import order_router
from vstitchapi.paymentApi import payment_router
from vstitchapi.productapi import product_router
from vstitchapi.signupapi import signup_router
from vstitchDatabase.schemaPersistence import SchemaPersistence


@asynccontextmanager
async def lifespan(app: FastAPI):
    schema_persistence = SchemaPersistence()
    schema_persistence.create_users_table_if_not_exists()
    yield


app = FastAPI(title="Vstitch Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(signup_router)
app.include_router(login_router)
app.include_router(order_router)
app.include_router(payment_router)
app.include_router(product_router)
app.include_router(category_router)
app.include_router(best_seller_router)


@app.get("/")
def read_root():
    return {"message": "Vstitch backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
