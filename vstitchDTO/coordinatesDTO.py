from pydantic import BaseModel, field_validator


class CoordinatesDTO(BaseModel):
    """Shared latitude/longitude fields + range validation - subclassed by
    SignupLocationDTO and UpdateLocationRequestDTO (distinct subclasses,
    not one shared type directly, so each keeps its own name in the OpenAPI
    schema) rather than duplicated per-DTO, since unlike a one-line regex
    constant this is real validation logic that both endpoints must agree
    on identically.
    """

    latitude: float
    longitude: float

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value):
        if not -90 <= value <= 90:
            raise ValueError("Enter a valid latitude.")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value):
        if not -180 <= value <= 180:
            raise ValueError("Enter a valid longitude.")
        return value
