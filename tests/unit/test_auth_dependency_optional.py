import pytest
from fastapi import HTTPException

from vstitchServices.authDependency import get_current_user_optional, jwt_token_service


class _FakeRequest:
    """Minimal stand-in for fastapi.Request - get_current_user_optional only
    ever calls request.headers.get("Authorization"), so a real ASGI Request
    isn't needed to exercise it.
    """

    def __init__(self, authorization=None):
        self.headers = {} if authorization is None else {"Authorization": authorization}


def _valid_token():
    return jwt_token_service.generate_access_token(7, "vansh_dev")


def test_returns_none_when_header_is_absent():
    assert get_current_user_optional(_FakeRequest()) is None


def test_resolves_user_from_a_valid_bearer_token():
    result = get_current_user_optional(_FakeRequest(f"Bearer {_valid_token()}"))
    assert result["vstitch_user_id"] == 7
    assert result["vstitch_user_name"] == "vansh_dev"


def test_raises_401_on_expired_or_garbage_token():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_optional(_FakeRequest("Bearer not-a-real-token"))
    assert exc_info.value.status_code == 401


def test_raises_401_on_wrong_auth_scheme():
    # Regression guard: a present-but-wrong-scheme header (e.g. "Basic ...")
    # used to be silently treated as anonymous by HTTPBearer(auto_error=False)
    # - it must now be rejected as a real auth failure, not downgraded.
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_optional(_FakeRequest(f"Basic {_valid_token()}"))
    assert exc_info.value.status_code == 401


def test_raises_401_on_malformed_header_with_no_token():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_optional(_FakeRequest("Bearer"))
    assert exc_info.value.status_code == 401
