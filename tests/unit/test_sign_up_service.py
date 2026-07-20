from unittest.mock import MagicMock

import pytest

from vstitchDTO.signupRequestDTO import SignupRequestDTO
from vstitchServices.signUpService import SignUpService

VALID_PAYLOAD = {
    "vstitch_user_name": "vansh_dev",
    "password": "Str0ngPass!",
    "first_name": "Vansh",
    "last_name": "Duggal",
    "email": "vansh@example.com",
    "phone_number": "+919876543210",
}


@pytest.fixture
def sign_up_service():
    service = SignUpService()
    service.signup_persistence = MagicMock()
    return service


def test_registers_a_new_user(sign_up_service):
    sign_up_service.signup_persistence.is_username_taken.return_value = False
    sign_up_service.signup_persistence.is_email_taken.return_value = False
    sign_up_service.signup_persistence.is_phone_number_taken.return_value = False
    sign_up_service.signup_persistence.create_user.return_value = (1, "vansh_dev", "vansh@example.com", None)

    response = sign_up_service.register_user(SignupRequestDTO(**VALID_PAYLOAD), "127.0.0.1")

    assert response.vstitch_user_id == 1
    assert response.vstitch_user_name == "vansh_dev"
    sign_up_service.signup_persistence.create_user.assert_called_once()


def test_rejects_duplicate_username(sign_up_service):
    sign_up_service.signup_persistence.is_username_taken.return_value = True

    with pytest.raises(ValueError, match="username"):
        sign_up_service.register_user(SignupRequestDTO(**VALID_PAYLOAD), "127.0.0.1")

    sign_up_service.signup_persistence.create_user.assert_not_called()


def test_rejects_duplicate_email(sign_up_service):
    sign_up_service.signup_persistence.is_username_taken.return_value = False
    sign_up_service.signup_persistence.is_email_taken.return_value = True

    with pytest.raises(ValueError, match="email"):
        sign_up_service.register_user(SignupRequestDTO(**VALID_PAYLOAD), "127.0.0.1")

    sign_up_service.signup_persistence.create_user.assert_not_called()


def test_rejects_duplicate_phone_number(sign_up_service):
    sign_up_service.signup_persistence.is_username_taken.return_value = False
    sign_up_service.signup_persistence.is_email_taken.return_value = False
    sign_up_service.signup_persistence.is_phone_number_taken.return_value = True

    with pytest.raises(ValueError, match="phone"):
        sign_up_service.register_user(SignupRequestDTO(**VALID_PAYLOAD), "127.0.0.1")

    sign_up_service.signup_persistence.create_user.assert_not_called()
