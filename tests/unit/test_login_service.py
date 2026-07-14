from unittest.mock import MagicMock

import pytest

from vstitchDTO.loginRequestDTO import LoginRequestDTO
from vstitchServices.loginService import LoginService


@pytest.fixture
def login_service(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-for-unit-tests")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    service = LoginService()
    service.login_persistence = MagicMock()
    return service


def test_authenticates_with_correct_password(login_service):
    hashed_password = login_service.password_hash_service.hash_password("Str0ngPass!")
    login_service.login_persistence.get_user_by_username.return_value = {
        "vstitch_user_id": 1,
        "vstitch_user_name": "vansh_dev",
        "vstitch_password": hashed_password,
    }

    response = login_service.authenticate_user(
        LoginRequestDTO(vstitch_user_name="vansh_dev", password="Str0ngPass!")
    )

    assert response.vstitch_user_id == 1
    assert response.token_type == "bearer"
    assert response.access_token


def test_rejects_wrong_password(login_service):
    hashed_password = login_service.password_hash_service.hash_password("Str0ngPass!")
    login_service.login_persistence.get_user_by_username.return_value = {
        "vstitch_user_id": 1,
        "vstitch_user_name": "vansh_dev",
        "vstitch_password": hashed_password,
    }

    with pytest.raises(ValueError, match="Invalid username or password"):
        login_service.authenticate_user(
            LoginRequestDTO(vstitch_user_name="vansh_dev", password="WrongPass!")
        )


def test_rejects_unknown_username(login_service):
    login_service.login_persistence.get_user_by_username.return_value = None

    with pytest.raises(ValueError, match="Invalid username or password"):
        login_service.authenticate_user(
            LoginRequestDTO(vstitch_user_name="nobody", password="whatever")
        )
