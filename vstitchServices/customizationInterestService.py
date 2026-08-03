import logging
import os

from vstitchDatabase.customizationInterestPersistence import CustomizationInterestPersistence
from vstitchServices.customizationInterestEmailTemplate import (
    HIGH_PRIORITY_EMAIL_HEADERS,
    build_customization_interest_email,
)
from vstitchServices.resendEmailClient import ResendEmailClient

logger = logging.getLogger(__name__)

# VSTITCH_CUSTOMIZED_USER.created_by value for every lead saved through this
# endpoint - identifies the submission channel, matching how
# CUSTOMIZATION_REQUEST_SOURCE labels bespoke-measurement requests in
# customizationRequestService.py, not a per-row "who".
LEAD_SOURCE = "vstitch-ai-widget"


class CustomizationInterestEmailError(Exception):
    """Raised when the admin notification email could not be sent or isn't
    configured - the one failure mode this feature's API layer reports back
    to the caller as a 500. Sending this email is this endpoint's actual
    deliverable (it's what replaces the mailto: fallback), unlike
    OrderEmailService's confirmation emails, which must never fail the
    order/payment flow that triggered them - so unlike that service, a
    failure here is deliberately allowed to propagate, wrapped in this
    dedicated type rather than a bare Exception so the API layer can catch
    exactly this failure mode without also swallowing unrelated bugs.
    """


class CustomizationInterestService:
    """Business logic for the VStitch AI widget's "Need a Custom Outfit?"
    lead form: persists the lead (best-effort - a valuable record for
    follow-up/leads-generation even if the notification below fails) and
    sends a high-priority admin notification email (must succeed - see
    CustomizationInterestEmailError).
    """

    def __init__(self):
        self.customization_interest_persistence = CustomizationInterestPersistence()

    def submit_interest(self, request_dto):
        """Raises CustomizationInterestEmailError if the admin notification
        couldn't be sent. Never raises anything else - a lead-persistence
        failure is logged and swallowed here, not surfaced, since the
        customer-facing contract for this endpoint is entirely about
        whether the studio was notified, not whether a lead row exists.
        """
        self._save_lead(request_dto)
        self._send_admin_notification(request_dto)

    def _save_lead(self, request_dto):
        try:
            self.customization_interest_persistence.save_lead(
                request_dto.name, request_dto.phone, request_dto.email, LEAD_SOURCE
            )
        except Exception:
            logger.exception(
                "Failed to persist customization-interest lead for %s - continuing to send the admin "
                "notification email regardless, since the lead record is a value-add for follow-up, not "
                "this endpoint's core deliverable.",
                request_dto.email,
            )

    def _send_admin_notification(self, request_dto):
        # VSTITCH_ADMIN_NOTIFICATION_EMAIL, deliberately separate from
        # VSTITCH_RESEND_EMAIL (the Resend "from" sender, which must be on
        # a domain verified with Resend) - see the matching comment in
        # OrderEmailService._send_admin_email for why conflating the two
        # silently sent every admin notification to a send-only noreply@
        # address instead of the studio's actual inbox.
        admin_email = os.getenv("VSTITCH_ADMIN_NOTIFICATION_EMAIL")
        if not admin_email:
            logger.error(
                "VSTITCH_ADMIN_NOTIFICATION_EMAIL is not configured - cannot send the "
                "customization-interest notification email for %s.",
                request_dto.email,
            )
            raise CustomizationInterestEmailError("Admin notification email is not configured.")

        try:
            resend_client = ResendEmailClient()
        except ValueError as configuration_error:
            logger.exception(
                "Resend is not configured - customization-interest notification email cannot be sent "
                "for %s.",
                request_dto.email,
            )
            raise CustomizationInterestEmailError("Email sending is not configured.") from configuration_error

        try:
            subject, text_body = build_customization_interest_email(
                request_dto.name, request_dto.phone, request_dto.email
            )
            resend_client.send_email(
                admin_email,
                subject,
                text_body=text_body,
                headers=HIGH_PRIORITY_EMAIL_HEADERS,
            )
        except Exception as send_error:
            logger.exception(
                "Failed to send customization-interest notification email for %s.",
                request_dto.email,
            )
            raise CustomizationInterestEmailError("Failed to send the notification email.") from send_error
