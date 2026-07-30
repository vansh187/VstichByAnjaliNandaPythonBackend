class InvalidReferenceError(ValueError):
    """Raised by persistence methods that translate a Postgres
    ForeignKeyViolation or CheckViolation into a business-rule error - a
    ValueError subclass so any caller that only catches ValueError still
    catches this, while a caller that wants to distinguish "the request body
    itself is invalid" (422) from "not found" (404) or "duplicate" (409, see
    UniqueConstraintError) can catch this specifically, ahead of a plain
    ValueError, without inspecting message text.
    """
