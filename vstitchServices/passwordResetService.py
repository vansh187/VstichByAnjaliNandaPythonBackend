import logging
import secrets
from datetime import datetime, timedelta

from vstitchDatabase.passwordResetPersistence import PasswordResetPersistence
from vstitchServices.passwordHashService import DUMMY_PASSWORD_HASH, PasswordHashService
from vstitchServices.passwordResetOtpEmailTemplate import build_password_reset_otp_email
from vstitchServices.resendEmailClient import ResendEmailClient

logger = logging.getLogger(__name__)

# VSTITCH_PASSWORD_RESET_OTPS.created_by/updated_by value for every row
# touched through this flow - identifies the source, same convention as
# GoogleAuthService/CustomizationInterestService's own source constants.
OTP_SOURCE = "password-reset-otp"

OTP_EXPIRY_MINUTES = 10
# Blocks a resend for the same account within this window - the request
# endpoint still always reports "sent" during the cooldown (never reveals
# it), this just skips actually generating/emailing a new code so "Resend"
# spam can't be used to flood one inbox or burn through Resend's quota.
OTP_RESEND_COOLDOWN_SECONDS = 60
# Caps failed /confirm attempts against one outstanding code - the real
# brute-force defense for a 6-digit (1-in-a-million) code, since the
# per-IP @limiter.limit alone would still allow thousands of guesses/day
# from a single IP.
MAX_OTP_ATTEMPTS = 5


def _utc_now():
    # Naive UTC, deliberately not timezone-aware: VSTITCH_PASSWORD_RESET_OTPS'
    # ExpiresAt/updated_date columns are plain TIMESTAMP (no timezone), and
    # psycopg2 round-trips those as naive datetimes - comparing an aware
    # datetime against those would raise TypeError. Every read/write in this
    # service goes through this one helper so both sides of every comparison
    # stay naive and in the same clock.
    return datetime.utcnow()


class PasswordResetRequestError(Exception):
    """A genuine infrastructure failure (email provider down/misconfigured,
    or an unexpected DB error) - the request endpoint's one failure mode
    that's allowed to surface as a real error, since it happens identically
    regardless of whether the email is registered and so can't be used to
    enumerate accounts."""


class InvalidOrExpiredOtpError(Exception):
    """The code in /confirm didn't match, was already used, or expired -
    mapped to 400. Deliberately one message for every one of these cases
    (see confirm_reset) so a caller can't distinguish "wrong code" from
    "no such account" from "code expired"."""


class TooManyOtpAttemptsError(Exception):
    """Too many wrong guesses against the current code - mapped to 429.
    Requesting a new code (which upserts/resets AttemptCount) is the only
    way out of this state."""


class PasswordResetService:
    """Business logic for the "Forgot password?" email-OTP flow: request_otp
    (send a code, never reveals whether the email is registered) and
    confirm_reset (verify the code and set the new password)."""

    def __init__(self):
        try:
            self.password_reset_persistence = PasswordResetPersistence()
            self.password_hash_service = PasswordHashService()
        except Exception as init_error:
            logger.exception("Failed to initialize PasswordResetService.")
            raise PasswordResetRequestError("Password reset is not available right now.") from init_error

    def request_otp(self, request_dto):
        """Never raises anything other than PasswordResetRequestError, and
        only for a genuine infrastructure failure - every other internal
        problem (no such account, DB hiccup looking the account up, still
        within the resend cooldown) is caught here and swallowed, so the API
        layer always reports the same generic "sent" success regardless of
        whether an email was actually sent. This is the enumeration
        protection the spec requires, implemented as "many internal
        early-outs, one external outcome" rather than a single if/else.
        """
        try:
            self._request_otp_unsafe(request_dto.email)
        except PasswordResetRequestError:
            raise
        except Exception:
            logger.exception(
                "Unexpected error while processing a password-reset OTP request for %s - reporting success "
                "regardless, since this must never differ from the 'no such account' response.",
                request_dto.email,
            )

    def _request_otp_unsafe(self, email):
        try:
            user_record = self.password_reset_persistence.get_user_by_email(email)
        except Exception:
            logger.exception("Failed to look up user by email for a password-reset OTP request.")
            user_record = None

        # Always generate and bcrypt-hash a code, even for a nonexistent
        # account - bcrypt (~250ms, per PasswordHashService's own comment)
        # is by far the dominant cost in this function, so skipping it only
        # on the "no such account" path would let a caller distinguish
        # registered from unregistered emails purely by response timing,
        # even though both return the identical {"status": "sent"} body.
        # Same technique as DUMMY_PASSWORD_HASH in login/admin-login.
        otp_code = f"{secrets.randbelow(1000000):06d}"
        otp_hash = self.password_hash_service.hash_password(otp_code)

        if user_record is None:
            return

        try:
            existing_otp = self.password_reset_persistence.get_otp_for_user(user_record["vstitch_user_id"])
        except Exception:
            logger.exception(
                "Failed to check for an existing OTP for user %s - proceeding to send a new one anyway.",
                user_record["vstitch_user_id"],
            )
            existing_otp = None

        if existing_otp is not None and existing_otp["consumed_at"] is None:
            seconds_since_last_send = (_utc_now() - existing_otp["updated_date"]).total_seconds()
            if 0 <= seconds_since_last_send < OTP_RESEND_COOLDOWN_SECONDS:
                return

        expires_at = _utc_now() + timedelta(minutes=OTP_EXPIRY_MINUTES)

        try:
            self.password_reset_persistence.save_otp(user_record["vstitch_user_id"], otp_hash, expires_at, OTP_SOURCE)
        except Exception:
            logger.exception("Failed to save a password-reset OTP for user %s.", user_record["vstitch_user_id"])
            return

        self._send_otp_email(user_record["email"], otp_code)

    def _send_otp_email(self, email, otp_code):
        try:
            resend_client = ResendEmailClient()
        except ValueError as configuration_error:
            logger.exception("Resend is not configured - password-reset OTP email cannot be sent.")
            raise PasswordResetRequestError("Email sending is not configured.") from configuration_error

        try:
            subject, text_body = build_password_reset_otp_email(otp_code, OTP_EXPIRY_MINUTES)
            resend_client.send_email(email, subject, text_body=text_body)
        except Exception as send_error:
            logger.exception("Failed to send a password-reset OTP email.")
            raise PasswordResetRequestError("Failed to send the reset code. Please try again later.") from send_error

    def confirm_reset(self, confirm_dto):
        """Raises InvalidOrExpiredOtpError, TooManyOtpAttemptsError, or
        PasswordResetRequestError - the API layer maps each to its own HTTP
        status. Every other exception is caught and re-raised as one of
        these three, so no raw exception can ever reach the caller."""
        try:
            user_record = self.password_reset_persistence.get_user_by_email(confirm_dto.email)
        except Exception:
            logger.exception("Failed to look up user by email during password-reset confirm.")
            user_record = None

        otp_record = None
        if user_record is not None:
            try:
                otp_record = self.password_reset_persistence.get_otp_for_user(user_record["vstitch_user_id"])
            except Exception:
                logger.exception(
                    "Failed to look up the OTP for user %s during confirm.", user_record["vstitch_user_id"]
                )
                otp_record = None

        # "Does a live OTP row exist" (account found, OTP found, unconsumed,
        # unexpired) is the enumeration-sensitive signal - deliberately
        # excludes attempt_count, since the attempt cap only matters once a
        # caller already knows a live OTP exists and isn't itself something
        # response timing needs to hide.
        otp_row_is_live = (
            otp_record is not None and otp_record["consumed_at"] is None and _utc_now() < otp_record["expires_at"]
        )

        # Always run bcrypt verification, even when there's no account or no
        # live OTP to check against (against a fixed dummy hash in that
        # case) - same DUMMY_PASSWORD_HASH technique loginService/
        # adminAuthService use for login, so response timing can't reveal
        # whether an account exists or currently has an OTP outstanding.
        # Same message either way below (InvalidOrExpiredOtpError), so a
        # caller can't distinguish "no account", "no OTP", "expired",
        # "already used", or "wrong code" from the response body either.
        otp_matches = self.password_hash_service.verify_password(
            confirm_dto.otp, otp_record["otp_hash"] if otp_row_is_live else DUMMY_PASSWORD_HASH
        )

        if otp_row_is_live and otp_record["attempt_count"] >= MAX_OTP_ATTEMPTS:
            raise TooManyOtpAttemptsError("Too many attempts - please request a new code.")

        if not otp_row_is_live or not otp_matches:
            if otp_row_is_live:
                self._register_failed_attempt(user_record["vstitch_user_id"])
            raise InvalidOrExpiredOtpError("Invalid or expired code.")

        self._finalize_reset(user_record["vstitch_user_id"], confirm_dto.new_password)

    def _register_failed_attempt(self, vstitch_user_id):
        """Best-effort - if the increment itself fails, the wrong-code
        rejection above still happens (InvalidOrExpiredOtpError is raised by
        the caller regardless), just without the attempt being counted this
        one time."""
        try:
            new_attempt_count = self.password_reset_persistence.increment_attempt_count(vstitch_user_id)
        except Exception:
            logger.exception("Failed to record a failed password-reset OTP attempt for user %s.", vstitch_user_id)
            return
        if new_attempt_count >= MAX_OTP_ATTEMPTS:
            raise TooManyOtpAttemptsError("Too many attempts - please request a new code.")

    def _finalize_reset(self, vstitch_user_id, new_password):
        new_password_hash = self.password_hash_service.hash_password(new_password)
        try:
            self.password_reset_persistence.finalize_password_reset(vstitch_user_id, new_password_hash, OTP_SOURCE)
        except Exception as update_error:
            logger.exception("Failed to finalize a password reset for user %s.", vstitch_user_id)
            raise PasswordResetRequestError(
                "Something went wrong while resetting your password. Please try again later."
            ) from update_error
