class UniqueConstraintError(ValueError):
    """Raised by persistence methods that translate a Postgres
    UniqueViolation into a business-rule error - a ValueError subclass so
    any caller that only catches ValueError still catches this, while a
    caller that wants to distinguish "duplicate" (409 Conflict) from
    "not found" (404) can catch this specifically, ahead of a plain
    ValueError, without inspecting message text.
    """


def translate_unique_violation(unique_violation, messages_by_constraint, default_message):
    """Shared translator for a caught psycopg2.errors.UniqueViolation -> a
    human-readable UniqueConstraintError, keyed off the violated
    constraint/index name (unique_violation.diag.constraint_name). Every
    persistence method that attempts an INSERT/UPDATE and catches the
    violation (rather than a racy check-then-insert) should call this
    instead of keeping its own copy of the same constraint-name lookup.
    """
    constraint_name = getattr(unique_violation.diag, "constraint_name", None)
    return UniqueConstraintError(messages_by_constraint.get(constraint_name, default_message))
