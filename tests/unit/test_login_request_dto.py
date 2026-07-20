import pytest
from pydantic import ValidationError

from vstitchDTO.loginRequestDTO import LoginRequestDTO


def test_accepts_valid_login_payload():
    dto = LoginRequestDTO(vstitch_user_name="vansh_dev", password="anything")
    assert dto.vstitch_user_name == "vansh_dev"


def test_rejects_missing_password():
    with pytest.raises(ValidationError):
        LoginRequestDTO(vstitch_user_name="vansh_dev")
