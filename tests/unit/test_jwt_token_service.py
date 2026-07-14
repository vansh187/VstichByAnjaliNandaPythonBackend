import pytest

from vstitchServices.jwtTokenService import JwtTokenService


@pytest.fixture
def jwt_token_service(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-for-unit-tests")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    return JwtTokenService()


def test_generate_and_decode_roundtrip(jwt_token_service):
    token = jwt_token_service.generate_access_token(vstitch_user_id=42, vstitch_user_name="vansh_dev")
    payload = jwt_token_service.decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["vstitch_user_name"] == "vansh_dev"


def test_decode_rejects_tampered_token(jwt_token_service):
    token = jwt_token_service.generate_access_token(vstitch_user_id=1, vstitch_user_name="someone")
    tampered_token = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(ValueError):
        jwt_token_service.decode_access_token(tampered_token)


def test_missing_secret_raises_value_error(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    with pytest.raises(ValueError):
        JwtTokenService()
