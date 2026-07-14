from vstitchDatabase.signupPersistence import SignupPersistence
from vstitchDTO.signupResponseDTO import SignupResponseDTO
from vstitchServices.passwordHashService import PasswordHashService


class SignUpService:
    """Business logic for creating a new VStitch_Users account."""

    def __init__(self):
        self.signup_persistence = SignupPersistence()
        self.password_hash_service = PasswordHashService()

    def register_user(self, signup_request_dto, created_by_ip_address):
        if self.signup_persistence.is_username_taken(signup_request_dto.vstitch_user_name):
            raise ValueError("This username is already taken.")
        if self.signup_persistence.is_email_taken(signup_request_dto.email):
            raise ValueError("An account with this email already exists.")
        if self.signup_persistence.is_phone_number_taken(signup_request_dto.phone_number):
            raise ValueError("An account with this phone number already exists.")

        hashed_password = self.password_hash_service.hash_password(signup_request_dto.password)

        inserted_row = self.signup_persistence.create_user(
            signup_request_dto.vstitch_user_name,
            hashed_password,
            signup_request_dto.first_name,
            signup_request_dto.last_name,
            signup_request_dto.email,
            signup_request_dto.phone_number,
            created_by_ip_address,
        )
        vstitch_user_id, vstitch_user_name, email, _created_date = inserted_row

        return SignupResponseDTO(
            vstitch_user_id=vstitch_user_id,
            vstitch_user_name=vstitch_user_name,
            email=email,
            message="Account created successfully.",
        )
