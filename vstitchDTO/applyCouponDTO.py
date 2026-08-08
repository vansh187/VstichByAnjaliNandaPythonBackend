from pydantic import BaseModel, Field, field_validator


class ApplyCouponRequestDTO(BaseModel):
    coupon_code: str = Field(..., min_length=1, max_length=50)
    order_amount: float = Field(..., gt=0)

    @field_validator("coupon_code")
    @classmethod
    def normalize_coupon_code(cls, value):
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("coupon_code cannot be blank.")
        return normalized


class ApplyCouponResponseDTO(BaseModel):
    coupon_code: str
    discount_amount: float
    final_amount: float
    message: str
