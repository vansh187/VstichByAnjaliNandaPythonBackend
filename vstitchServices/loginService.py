from vstitchDatabase.loginPersistence import LoginPersistence
from vstitchDTO.loginResponseDTO import LoginResponseDTO
from vstitchServices.jwtTokenService import JwtTokenService
from vstitchServices.passwordHashService import PasswordHashService


class LoginService:
    """Business logic for authenticating a VStitch_Users account."""

    def __init__(self):
        self.login_persistence = LoginPersistence()
        self.password_hash_service = PasswordHashService()
        self.jwt_token_service = JwtTokenService()

    def authenticate_user(self, login_request_dto):
        user_record = self.login_persistence.get_user_by_username(login_request_dto.vstitch_user_name)
        if user_record is None:
            raise ValueError("Invalid username or password.")

        password_matches = self.password_hash_service.verify_password(
            login_request_dto.password, user_record["vstitch_password"]
        )
        if not password_matches:
            raise ValueError("Invalid username or password.")

        access_token = self.jwt_token_service.generate_access_token(
            user_record["vstitch_user_id"], user_record["vstitch_user_name"]
        )

        return LoginResponseDTO(
            access_token=access_token,
            token_type="bearer",
            vstitch_user_id=user_record["vstitch_user_id"],
            vstitch_user_name=user_record["vstitch_user_name"],
        )
