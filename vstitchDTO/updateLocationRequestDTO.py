from pydantic import BaseModel, Field, field_validator

from vstitchDTO.googleMapsLinkValidator import MAX_GOOGLE_MAPS_LINK_LENGTH, validate_google_maps_link


class UpdateLocationRequestDTO(BaseModel):
    google_maps_link: str = Field(..., min_length=1, max_length=MAX_GOOGLE_MAPS_LINK_LENGTH)

    @field_validator("google_maps_link")
    @classmethod
    def validate_google_maps_link_field(cls, value):
        return validate_google_maps_link(value)
