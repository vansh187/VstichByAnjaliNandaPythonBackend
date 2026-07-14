from fastapi import FastAPI

from vstitchapi.loginapi import login_router
from vstitchapi.signupapi import signup_router
from vstitchDatabase.schemaPersistence import SchemaPersistence

app = FastAPI(title="Vstitch Backend", version="1.0.0")


@app.on_event("startup")
def initialize_database_schema():
    schema_persistence = SchemaPersistence()
    schema_persistence.create_users_table_if_not_exists()


app.include_router(signup_router)
app.include_router(login_router)


@app.get("/")
def read_root():
    return {"message": "Vstitch backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
