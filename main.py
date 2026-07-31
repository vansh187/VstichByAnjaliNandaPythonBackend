import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from vstitchServices.rateLimiter import limiter
from vstitchServices.securityHeadersMiddleware import SecurityHeadersMiddleware
from vstitchapi.adminAuditLogApi import admin_audit_log_router
from vstitchapi.adminAuthApi import admin_auth_router
from vstitchapi.adminCategoryApi import admin_category_router
from vstitchapi.adminImageApi import admin_image_router
from vstitchapi.adminOrderApi import admin_order_router
from vstitchapi.adminProductApi import admin_product_router
from vstitchapi.adminReturnApi import admin_return_router
from vstitchapi.adminRevenueApi import admin_revenue_router
from vstitchapi.adminShipmentApi import admin_shipment_router
from vstitchapi.bestSellerApi import best_seller_router
from vstitchapi.categoryapi import category_router
from vstitchapi.googleAuthApi import google_auth_router
from vstitchapi.loginapi import login_router
from vstitchapi.orderapi import order_router
from vstitchapi.paymentApi import payment_router
from vstitchapi.productapi import product_router
from vstitchapi.reviewApi import review_router
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
    schema_persistence.create_admin_users_table_if_not_exists()
    schema_persistence.create_admin_audit_log_table_if_not_exists()
    yield


app = FastAPI(title="Vstitch Backend", version="1.0.0", lifespan=lifespan)

app.state.limiter = limiter


def _rate_limit_exceeded_handler(request, exc):
    # Same "generic message, no internals" convention as every other error
    # path in this codebase, rather than slowapi's default {"error": ...}
    # shape.
    return JSONResponse(status_code=429, content={"detail": "Too many requests - please try again shortly."})


app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Real frontend origin(s) aren't finalized yet - read from an env var
# (comma-separated) rather than hardcoding, falling back to the common local
# dev ports so local development isn't broken in the meantime. See
# .env.example for the ALLOWED_ORIGINS format.
_allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "").strip()
allowed_origins = (
    [origin.strip() for origin in _allowed_origins_env.split(",") if origin.strip()]
    if _allowed_origins_env
    else ["http://localhost:5173", "http://localhost:3000"]
)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SlowAPIMiddleware)

app.include_router(signup_router)
app.include_router(login_router)
app.include_router(google_auth_router)
app.include_router(order_router)
app.include_router(payment_router)
app.include_router(product_router)
app.include_router(review_router)
app.include_router(category_router)
app.include_router(best_seller_router)
app.include_router(shipment_router)
app.include_router(shipment_ops_router)
app.include_router(admin_auth_router)
app.include_router(admin_audit_log_router)
app.include_router(admin_order_router)
app.include_router(admin_revenue_router)
app.include_router(admin_category_router)
app.include_router(admin_image_router)
app.include_router(admin_product_router)
app.include_router(admin_return_router)
app.include_router(admin_shipment_router)


@app.get("/")
def read_root():
    return {"message": "Vstitch backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
