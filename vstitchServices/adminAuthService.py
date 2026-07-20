from vstitchDatabase.adminUserPersistence import AdminUserPersistence
from vstitchDTO.adminLoginResponseDTO import AdminLoginResponseDTO
from vstitchServices.adminJwtTokenService import AdminJwtTokenService
from vstitchServices.passwordHashService import PasswordHashService


class AdminAuthService:
    """Business logic for authenticating a VStitch_AdminUsers account."""

    def __init__(self):
        self.admin_user_persistence = AdminUserPersistence()
        self.password_hash_service = PasswordHashService()
        self.admin_jwt_token_service = AdminJwtTokenService()

    def login(self, admin_login_request_dto):
        admin_record = self.admin_user_persistence.get_admin_by_username(
            admin_login_request_dto.admin_username
        )
        # Same message whether the username doesn't exist or the password is
        # wrong - distinguishing the two would let a caller enumerate valid
        # admin usernames.
        if admin_record is None or not admin_record["is_active"]:
            raise ValueError("Invalid admin username or password.")

        password_matches = self.password_hash_service.verify_password(
            admin_login_request_dto.password, admin_record["admin_password"]
        )
        if not password_matches:
            raise ValueError("Invalid admin username or password.")

        access_token = self.admin_jwt_token_service.generate_access_token(
            admin_record["vstitch_admin_id"], admin_record["admin_username"]
        )

        return AdminLoginResponseDTO(
            access_token=access_token,
            token_type="bearer",
            admin_id=admin_record["vstitch_admin_id"],
            admin_username=admin_record["admin_username"],
        )
