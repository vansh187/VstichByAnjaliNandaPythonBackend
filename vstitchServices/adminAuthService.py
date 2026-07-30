from vstitchDatabase.adminUserPersistence import AdminUserPersistence
from vstitchDTO.adminLoginResponseDTO import AdminLoginResponseDTO
from vstitchServices.adminJwtTokenService import AdminJwtTokenService
from vstitchServices.passwordHashService import DUMMY_PASSWORD_HASH, PasswordHashService


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
        # Always run bcrypt verification, even when the username doesn't
        # exist or is inactive (against a fixed dummy hash in that case) -
        # see DUMMY_PASSWORD_HASH's comment. Same message either way, and
        # now the same response timing too - distinguishing either would let
        # a caller enumerate valid admin usernames.
        account_is_usable = admin_record is not None and admin_record["is_active"]
        real_password_hash = admin_record["admin_password"] if account_is_usable else None
        password_matches = self.password_hash_service.verify_password(
            admin_login_request_dto.password, real_password_hash or DUMMY_PASSWORD_HASH
        )
        if not account_is_usable or not password_matches:
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

    def revoke_all_sessions(self, vstitch_admin_id, updated_by):
        """'Log out everywhere' - see AdminUserPersistence.revoke_all_sessions
        and adminAuthDependency.get_current_admin for how this is enforced."""
        self.admin_user_persistence.revoke_all_sessions(vstitch_admin_id, updated_by)

    def reset_password(self, admin_reset_password_request_dto):
        """No self-serve 'forgot password' email flow exists (see
        scripts/create_admin_user.py's docstring on why there's no self-serve
        admin signup either) - this requires knowing both the admin's
        username AND their registered email, which keeps a bare username
        guess from being enough to hijack the account. Same generic error
        either way (unknown username, wrong email, or inactive account) so
        the response doesn't reveal which part was wrong.
        """
        new_password_hash = self.password_hash_service.hash_password(
            admin_reset_password_request_dto.new_password
        )
        was_reset = self.admin_user_persistence.reset_password(
            admin_reset_password_request_dto.admin_username,
            admin_reset_password_request_dto.email,
            new_password_hash,
            f"admin-self-service-reset:{admin_reset_password_request_dto.admin_username}",
        )
        if not was_reset:
            raise ValueError("No matching admin account found for that username and email.")
