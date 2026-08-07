import logging

from vstitchDatabase.userLocationPersistence import UserLocationPersistence

logger = logging.getLogger(__name__)

# VStitch_Users.updated_by value for every row touched through this
# endpoint - identifies the source, same convention as GoogleAuthService/
# SubscriberService's own source constants.
LOCATION_UPDATE_SOURCE = "user-location-update"


class UserLocationUpdateError(Exception):
    """A genuine infrastructure/DB failure while saving the user's
    location - the endpoint's one failure mode, mapped to 500."""


class UserLocationService:
    """Business logic for POST /users/location: updates the authenticated
    user's saved latitude/longitude."""

    def __init__(self):
        try:
            self.user_location_persistence = UserLocationPersistence()
        except Exception as init_error:
            logger.exception("Failed to initialize UserLocationService.")
            raise UserLocationUpdateError("Location saving is not available right now.") from init_error

    def update_location(self, vstitch_user_id, update_location_request_dto):
        try:
            self.user_location_persistence.update_location(
                vstitch_user_id,
                update_location_request_dto.latitude,
                update_location_request_dto.longitude,
                LOCATION_UPDATE_SOURCE,
            )
        except Exception as update_error:
            logger.exception("Failed to update location for user %s.", vstitch_user_id)
            raise UserLocationUpdateError(
                "Something went wrong while saving your location. Please try again later."
            ) from update_error
