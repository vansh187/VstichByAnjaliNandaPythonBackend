# VStitch Backend

Backend for the VStitch ecommerce platform (women's clothing) - Python, FastAPI, PostgreSQL (Supabase).

## Tech stack

- **API**: FastAPI, class-based routers (`vstitchapi/`)
- **Business logic**: plain Python service classes (`vstitchServices/`)
- **Persistence**: psycopg2 against PostgreSQL, SQL kept in YAML files (`sqlQueries/`), loaded and executed by persistence classes (`vstitchDatabase/`)
- **Validation**: Pydantic DTOs (`vstitchDTO/`)
- **Auth**: bcrypt password hashing, JWT (HS256) via `python-jose`
- **Database**: PostgreSQL hosted on Supabase
- **Tests**: pytest (unit tests with mocked persistence + integration tests against a real Postgres)
- **CI**: GitHub Actions, running against an ephemeral Postgres service container

## Architecture / naming conventions

| Layer | Folder | Convention |
|---|---|---|
| API | `vstitchapi/` | class-based FastAPI routers, one file per feature (`signupapi.py`, `loginapi.py`) |
| Service | `vstitchServices/` | business logic classes, suffixed `Service` (`SignUpService`, `LoginService`, `PasswordHashService`, `JwtTokenService`) |
| Persistence | `vstitchDatabase/` | DB access classes, suffixed `Persistence` (`SignupPersistence`, `LoginPersistence`, `SchemaPersistence`); `ConnectionFactory` owns the connection pool, `QueryLoader` reads SQL out of `sqlQueries/*.yaml` |
| DTO | `vstitchDTO/` | Pydantic request/response models, validation lives here (email/phone format, password length, etc.) |
| SQL | `sqlQueries/*.yaml` | raw SQL keyed by name, loaded by `QueryLoader` - never inline SQL strings in Python |
| Schema | `vstitchDatabase/schema/*.sql` | one `CREATE TABLE` file per table, applied directly to Postgres |

All classes are plain OOP (no `@staticmethod`); all tables use `BIGSERIAL` surrogate keys and the audit columns `created_by` / `created_date` / `updated_by` / `updated_date` (the `_by` columns store the request's IP address).

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements-dev.txt   # includes requirements.txt + pytest/httpx
```

Create a `.env` in the project root (never committed - see `.gitignore`) with:

```
JWT_SECRET=...
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<database>
```

## Running locally

```bash
uvicorn main:app --reload
```

Docs at `http://127.0.0.1:8000/docs`. `VStitch_Users` is created automatically on startup if it doesn't exist (`SchemaPersistence`, via the FastAPI `lifespan` handler in `main.py`).

## Testing

```bash
pytest                                  # unit tests only (no DB writes)
RUN_API_INTEGRATION_TESTS=1 pytest      # also runs tests/integration against a real Postgres - set DATABASE_URL to a throwaway DB first
```

CI (`.github/workflows/ci.yml`) runs both automatically against a disposable Postgres container on every PR into `main`. Direct pushes to `main` are blocked - all changes go through a PR that must pass CI.

## Deploying (Render)

Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`. Set `DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` as environment variables on the Render service - `.env` is not committed, so Render needs its own copy.

## Database schema

12 tables total. `VStitch_Users`, `VStitch_Orders`, and `VStitch_OrderItems` are built and wired into the API; the other 9 exist in the database (applied directly to Supabase) but are not yet wired into persistence/service/API classes - that's upcoming work.

| Table | Purpose |
|---|---|
| `VStitch_Users` | Signup/login accounts. Password stored as a bcrypt hash; JWT is issued on successful login. |
| `VStitch_Categories` | Category tree for the catalog (self-referencing `ParentCategoryId`, e.g. Sarees -> sub-styles). Women's-only catalog, no gender split needed in the schema. |
| `VStitch_Products` | Core product info (name, description, category, display-only base price). The actual sellable unit is a variant, not the product row itself. |
| `VStitch_ProductVariants` | Size/color combinations of a product, each with its own SKU, price, and stock count - this is what actually gets added to a cart. |
| `VStitch_ProductImages` | Product photos (stored as Supabase Storage URLs, not binary data in the DB). Optionally tagged to a specific variant for color-specific shots; left untagged for generic photos like a size chart. |
| `VStitch_Addresses` | Reusable shipping/billing addresses saved against a user account. |
| `VStitch_CartItems` | A customer's live cart - one row per (user, variant). No separate "cart" table; a cart has no attributes beyond its owner. |
| `VStitch_Orders` | A placed order. Snapshots the shipping address at checkout time so later address edits never rewrite order history. `OrderStatus` follows a cash-on-delivery pipeline (`placed -> confirmed -> processing -> shipped -> out_for_delivery -> delivered`, with `cancelled`/`delivery_failed` exits) - see `vstitchServices/orderStatus.py`. `PaymentMethod` is currently `cod` only. |
| `VStitch_OrderItems` | Line items of an order. Snapshots the product name/size/color/price at time of purchase, so later price changes or product renames never rewrite historical orders. |
| `VStitch_PaymentTransactions` | Payment gateway transaction attempts against an order (supports retries - a failed attempt followed by a successful one is two rows, not an overwrite). |
| `VStitch_Reviews` | One review per (user, product) - product-level, not tied to a specific size/color variant. |
| `VStitch_Wishlist` | One wishlist entry per (user, product) - product-level, same reasoning as reviews. |

Full DDL for each table lives in `vstitchDatabase/schema/*.sql`. One-off ALTERs applied directly against the live database live in `vstitchDatabase/schema/migrations/*.sql`.

## Workflow so far

1. **Signup/login API** - `VStitch_Users` table, DTOs with email/phone/password validation, bcrypt password hashing, JWT issuance on login, layered persistence/service/API classes. Verified end to end against the real database, including concurrent-signup and wrong-password/duplicate-account cases.
2. **CI/CD pipeline** - GitHub Actions workflow: installs deps, confirms the app imports/boots cleanly, runs the full pytest suite (unit tests mocked, integration tests against an ephemeral Postgres container). Branch protection added on `main`: no direct pushes, PR + passing CI required to merge.
3. **Full ecommerce schema design** - 11 additional tables (catalog, cart, orders, payments, reviews, wishlist) designed with variants/stock per size-color combination, loose coupling via `ON DELETE` behavior chosen per relationship, and snapshot columns on orders/order items so historical data survives later catalog/address changes.
4. **Schema review pass** - caught and fixed two Postgres NULL-uniqueness gaps (duplicate top-level category names, duplicate default-size/color variants) and clarified that `Products.BasePrice` is catalog-display-only, never used for checkout math.
5. **Applied to Supabase** - all 11 tables created directly against the live database, FK/cascade behavior verified against `pg_constraint`, both uniqueness fixes proven with live insert attempts (then rolled back, leaving no test data). `.sql` files committed to `vstitchDatabase/schema/`.
6. **Create-order API (cash on delivery)** - `POST /orders`, authenticated via the JWT issued at login. Validates each requested variant is active and in stock, snapshots product name/size/color/price onto `VStitch_OrderItems`, decrements `VStitch_ProductVariants.StockQuantity` with a race-safe conditional `UPDATE` (all inside one transaction), and creates the order with `OrderStatus = 'placed'`, `PaymentMethod = 'cod'`. Defined the full COD status pipeline (`vstitchServices/orderStatus.py`) and migrated the live `VStitch_Orders.OrderStatus` CHECK constraint off the old online-payment-shaped domain (`pending/paid/...`) to match. Verified end to end against the real database (successful order, missing auth, insufficient stock), then cleaned up all test data.

**Next up**: wire the remaining tables (`VStitch_Categories`, `VStitch_Products`, `VStitch_ProductVariants`, `VStitch_ProductImages`, `VStitch_Addresses`, `VStitch_CartItems`, `VStitch_PaymentTransactions`, `VStitch_Reviews`, `VStitch_Wishlist`) into `sqlQueries/*.yaml` + `<entity>Persistence.py` classes, then build the catalog/cart/order-status-update/admin APIs on top (see the delivery plan for the week-by-week breakdown).
