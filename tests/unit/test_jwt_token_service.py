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
    # Tamper a character in the *payload* segment, not the last character of
    # the whole token: the signature is HMAC'd over the literal
    # "header_b64.payload_b64" string, so any change there always produces a
    # different string and therefore always fails verification. The final
    # base64 group of the *signature* segment has spare/padding bits (32
    # HMAC-SHA256 bytes don't divide evenly into base64 sextets), so some
    # substitutions of the token's very last character decode to the exact
    # same signature bytes despite being a different character - that made
    # this test flaky (only ~1 in a few runs) rather than a real bug in
    # verification.
    token = jwt_token_service.generate_access_token(vstitch_user_id=1, vstitch_user_name="someone")
    header_b64, payload_b64, signature_b64 = token.split(".")
    middle_index = len(payload_b64) // 2
    original_char = payload_b64[middle_index]
    replacement_char = "A" if original_char != "A" else "B"
    tampered_payload_b64 = payload_b64[:middle_index] + replacement_char + payload_b64[middle_index + 1 :]
    tampered_token = f"{header_b64}.{tampered_payload_b64}.{signature_b64}"
    with pytest.raises(ValueError):
        jwt_token_service.decode_access_token(tampered_token)


def test_missing_secret_raises_value_error(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    with pytest.raises(ValueError):
        JwtTokenService()
