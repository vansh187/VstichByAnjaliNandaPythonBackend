GOOGLE_MAPS_LINK_PREFIX = "https://www.google.com/maps"
# TEXT columns have no DB-level length limit, but an unbounded string
# accepted straight from an unauthenticated-adjacent field (signup) or a
# bearer-token-authenticated one (update) is still worth capping - this is
# generous enough for any real Google Maps URL while rejecting abuse/
# garbage input outright rather than letting the app choke on it later.
MAX_GOOGLE_MAPS_LINK_LENGTH = 2048


def validate_google_maps_link(value):
    """Shared by SignupRequestDTO and UpdateLocationRequestDTO - a plain
    function rather than a shared base model, since the two DTOs disagree
    on whether the field itself is optional (signup) or required
    (update); only the validation logic, once a value is present, needs
    to be identical between them."""
    if len(value) > MAX_GOOGLE_MAPS_LINK_LENGTH or not value.startswith(GOOGLE_MAPS_LINK_PREFIX):
        raise ValueError("Enter a valid Google Maps URL.")
    return value
