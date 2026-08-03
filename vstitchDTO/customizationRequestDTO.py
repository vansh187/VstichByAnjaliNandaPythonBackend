from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# Sanity bound on the measurement fields (inches) - generous enough to never
# reject a real body measurement, tight enough to catch obvious garbage
# (e.g. a stray extra digit, or centimeters typed into an inches field)
# before it reaches the database as a plausible-looking row.
MIN_MEASUREMENT_IN = 0.1
MAX_MEASUREMENT_IN = 100

# VStitch_CustomizationRequests' measurement columns are NUMERIC(5,2) - the
# same 2-decimal-place precision razorpayClient.to_paise rounds to before
# handing an amount to Razorpay. Rounding here, not just at the DB, means
# the value validated and the value actually stored/echoed back in the
# response are always the same number, rather than the DB silently
# rounding a 3-decimal input after the fact with no validation error.
MEASUREMENT_DECIMAL_PLACES = Decimal("0.01")

MEASUREMENT_FIELD_NAMES = (
    "bust_in",
    "waist_in",
    "hips_in",
    "shoulder_in",
    "sleeve_length_in",
    "dress_length_in",
)


class CreateCustomizationRequestDTO(BaseModel):
    # max_length matches VStitch_CustomizationRequests.CustomerName/
    # CustomerPhone's VARCHAR(250)/VARCHAR(50) exactly, so an over-length
    # value fails validation (422) here instead of surfacing as an
    # unhandled StringDataRightTruncation from the database.
    customer_name: str = Field(..., min_length=1, max_length=250)
    customer_phone: str = Field(..., min_length=7, max_length=50)
    bust_in: float = Field(..., ge=MIN_MEASUREMENT_IN, le=MAX_MEASUREMENT_IN)
    waist_in: float = Field(..., ge=MIN_MEASUREMENT_IN, le=MAX_MEASUREMENT_IN)
    hips_in: float = Field(..., ge=MIN_MEASUREMENT_IN, le=MAX_MEASUREMENT_IN)
    shoulder_in: float = Field(..., ge=MIN_MEASUREMENT_IN, le=MAX_MEASUREMENT_IN)
    sleeve_length_in: float = Field(..., ge=MIN_MEASUREMENT_IN, le=MAX_MEASUREMENT_IN)
    dress_length_in: float = Field(..., ge=MIN_MEASUREMENT_IN, le=MAX_MEASUREMENT_IN)
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("customer_name", "customer_phone")
    @classmethod
    def reject_blank_text(cls, value):
        # min_length already rejects a too-short/empty string, but not one
        # made entirely of whitespace ("   ") - that passes min_length yet
        # is exactly as useless to the studio calling/addressing the
        # customer back.
        if not value.strip():
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator(*MEASUREMENT_FIELD_NAMES)
    @classmethod
    def round_to_db_precision(cls, value):
        return float(Decimal(str(value)).quantize(MEASUREMENT_DECIMAL_PLACES, rounding=ROUND_HALF_UP))
