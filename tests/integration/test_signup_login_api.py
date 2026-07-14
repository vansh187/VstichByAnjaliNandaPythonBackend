import os
import uuid

import pytest
from fastapi.testclient import TestClient

from main import app

# These tests exercise the real /signup and /login HTTP surface against a
# real Postgres database (schema creation runs via the app's startup event).
# Guarded behind an explicit opt-in so a stray local `pytest` run never
# creates rows against whatever DATABASE_URL happens to be in .env - CI sets
# RUN_API_INTEGRATION_TESTS=1 against an ephemeral, throwaway Postgres.
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_API_INTEGRATION_TESTS") != "1",
        reason="Set RUN_API_INTEGRATION_TESTS=1 to run integration tests against a real Postgres database.",
    ),
]


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _unique_signup_payload():
    unique_digits = str(uuid.uuid4().int)[:8]
    return {
        "vstitch_user_name": f"ci_user_{unique_digits}",
        "password": "Str0ngPass!",
        "first_name": "CI",
        "last_name": "Tester",
        "email": f"ci_user_{unique_digits}@example.com",
        "phone_number": f"9{unique_digits}0000",
    }


def test_signup_then_login_returns_valid_token(client):
    payload = _unique_signup_payload()

    signup_response = client.post("/signup", json=payload)
    assert signup_response.status_code == 200
    assert signup_response.json()["vstitch_user_name"] == payload["vstitch_user_name"]

    login_response = client.post(
        "/login",
        json={"vstitch_user_name": payload["vstitch_user_name"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    login_body = login_response.json()
    assert login_body["token_type"] == "bearer"
    assert login_body["access_token"]


def test_login_with_wrong_password_returns_401(client):
    payload = _unique_signup_payload()
    client.post("/signup", json=payload)

    login_response = client.post(
        "/login",
        json={"vstitch_user_name": payload["vstitch_user_name"], "password": "WrongPassword!"},
    )
    assert login_response.status_code == 401


def test_duplicate_signup_returns_409(client):
    payload = _unique_signup_payload()
    first_response = client.post("/signup", json=payload)
    assert first_response.status_code == 200

    second_response = client.post("/signup", json=payload)
    assert second_response.status_code == 409


def test_login_unknown_user_returns_401(client):
    response = client.post(
        "/login", json={"vstitch_user_name": "does_not_exist_xyz", "password": "whatever123"}
    )
    assert response.status_code == 401
