from fastapi import APIRouter, Depends, HTTPException

from vstitchDTO.updateLocationRequestDTO import UpdateLocationRequestDTO
from vstitchDTO.updateLocationResponseDTO import UpdateLocationResponseDTO
from vstitchServices.authDependency import get_current_user
from vstitchServices.userLocationService import UserLocationService, UserLocationUpdateError


class UserLocationApi:
    """Exposes POST /users/location - refreshes the authenticated user's
    saved geolocation on login (email/password or Google), mirroring the
    optional location fields captured at signup. Auth-gated (the user is
    identified from the token, never a body field), so unlike /signup or
    /subscribe this isn't rate-limited - the abuse surface a per-IP limiter
    exists for elsewhere (unauthenticated writes) doesn't apply here.
    """

    def __init__(self):
        self.user_location_service = UserLocationService()
        self.router = APIRouter(prefix="/users")
        self.router.add_api_route(
            "/location",
            self.update_location,
            methods=["POST"],
            response_model=UpdateLocationResponseDTO,
        )

    def update_location(
        self,
        update_location_request_dto: UpdateLocationRequestDTO,
        current_user: dict = Depends(get_current_user),
    ):
        try:
            self.user_location_service.update_location(current_user["vstitch_user_id"], update_location_request_dto)
        except UserLocationUpdateError as update_error:
            raise HTTPException(status_code=500, detail=str(update_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong. Please try again later.",
            )
        return UpdateLocationResponseDTO(status="updated")


user_location_api = UserLocationApi()
user_location_router = user_location_api.router
