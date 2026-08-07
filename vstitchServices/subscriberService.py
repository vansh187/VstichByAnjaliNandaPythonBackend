import logging

from vstitchDatabase.subscriberPersistence import SubscriberPersistence

logger = logging.getLogger(__name__)

# VSTITCH_SUBSCRIBERS.created_by/updated_by value for every row saved
# through this endpoint - identifies the submission channel, same
# convention as CustomizationInterestService.LEAD_SOURCE.
SUBSCRIBER_SOURCE = "newsletter-subscribe-widget"


class SubscriptionError(Exception):
    """Raised when a newsletter subscription could not be saved - the one
    failure mode the API layer reports back to the caller as a 500."""


class SubscriberService:
    """Business logic for the newsletter "Subscribe" form: saves the email
    to VSTITCH_SUBSCRIBERS. No auth, no email required to be sent - the
    subscription itself is the entire deliverable, unlike
    CustomizationInterestService's lead + notification-email pair.
    """

    def __init__(self):
        try:
            self.subscriber_persistence = SubscriberPersistence()
        except Exception as init_error:
            logger.exception("Failed to initialize SubscriberService.")
            raise SubscriptionError("Subscription service is not available right now.") from init_error

    def subscribe(self, request_dto):
        """Saves (or re-confirms) a subscriber. Never raises anything other
        than SubscriptionError - every other exception is caught, logged,
        and translated here so the API layer only ever has one failure mode
        to handle."""
        try:
            saved_subscriber = self.subscriber_persistence.save_subscriber(
                request_dto.email, SUBSCRIBER_SOURCE, SUBSCRIBER_SOURCE
            )
        except Exception as save_error:
            logger.exception("Failed to save newsletter subscription for %s.", request_dto.email)
            raise SubscriptionError("Could not complete your subscription. Please try again later.") from save_error

        return {
            "status": "subscribed",
            "vstitch_subscriber_id": saved_subscriber["vstitch_subscriber_id"],
            "email": saved_subscriber["email"],
            "created_date": saved_subscriber["created_date"],
            "updated_date": saved_subscriber["updated_date"],
        }
