import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vstitchapi.bestSellerApi import best_seller_router
from vstitchapi.categoryapi import category_router
from vstitchapi.loginapi import login_router
from vstitchapi.orderapi import order_router
from vstitchapi.paymentApi import payment_router
from vstitchapi.productapi import product_router
from vstitchapi.shipmentApi import shipment_router
from vstitchapi.shipmentOpsApi import shipment_ops_router
from vstitchapi.signupapi import signup_router
from vstitchDatabase.schemaPersistence import SchemaPersistence

# Root config for every module-level `logging.getLogger(__name__)` in the
# app (e.g. PaymentService's shipment-failure logging) - without this call
# those loggers fall back to the "handler of last resort", which prints
# only WARNING+ with no timestamp/module name, so failures are hard to find
# and correlate in production logs.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


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
app.include_router(shipment_router)
app.include_router(shipment_ops_router)


@app.get("/")
def read_root():
    return {"message": "Vstitch backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
