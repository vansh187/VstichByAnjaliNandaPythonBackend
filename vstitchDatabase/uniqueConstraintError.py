class UniqueConstraintError(ValueError):
    """Raised by persistence methods that translate a Postgres
    UniqueViolation into a business-rule error - a ValueError subclass so
    any caller that only catches ValueError still catches this, while a
    caller that wants to distinguish "duplicate" (409 Conflict) from
    "not found" (404) can catch this specifically, ahead of a plain
    ValueError, without inspecting message text.
    """
