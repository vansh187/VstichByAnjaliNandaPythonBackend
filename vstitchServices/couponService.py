from vstitchDatabase.couponPersistence import CouponPersistence, InvalidCouponError
from vstitchDTO.applyCouponDTO import ApplyCouponResponseDTO
from vstitchDTO.couponResponseDTO import (
    AvailableCouponDTO,
    AvailableCouponsResponseDTO,
    CouponListResponseDTO,
    CouponResponseDTO,
)

# Percentage discounts are rounded to paise/cents; a flat discount is
# already an exact currency amount and needs no rounding.
DISCOUNT_ROUNDING_PLACES = 2


class CouponNotFoundError(ValueError):
    """No coupon exists with this code - mapped to 404, distinct from the
    plain ValueError below (inactive/threshold-not-met), which is a 409:
    the coupon *exists*, just can't be applied right now."""


class CouponService:
    """Business logic for coupon CRUD (admin), the public price-based
    coupon list, and the checkout apply flow."""

    def __init__(self):
        self.coupon_persistence = CouponPersistence()

    # --- Admin --------------------------------------------------------

    def create_coupon(self, create_coupon_request_dto, admin_username):
        row = self.coupon_persistence.create_coupon(
            create_coupon_request_dto.coupon_name,
            create_coupon_request_dto.coupon_code,
            create_coupon_request_dto.coupon_description,
            create_coupon_request_dto.discount_type,
            create_coupon_request_dto.discount_value,
            create_coupon_request_dto.min_order_amount,
            create_coupon_request_dto.is_active,
            f"admin:{admin_username}",
        )
        return self._to_coupon_dto(row)

    def get_coupon(self, vstitch_coupon_id):
        row = self.coupon_persistence.get_coupon_by_id(vstitch_coupon_id)
        if row is None:
            raise ValueError(f"Coupon {vstitch_coupon_id} was not found.")
        return self._to_coupon_dto(row)

    def list_coupons_admin(self, after_id, limit):
        rows = self.coupon_persistence.list_coupons_admin(after_id, limit + 1)
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = page_rows[-1]["vstitch_coupon_id"] if has_more and page_rows else None
        return CouponListResponseDTO(
            items=[self._to_coupon_dto(row) for row in page_rows],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def update_coupon(self, vstitch_coupon_id, update_coupon_request_dto, admin_username):
        current = self.coupon_persistence.get_coupon_by_id(vstitch_coupon_id)
        if current is None:
            raise ValueError(f"Coupon {vstitch_coupon_id} was not found.")

        supplied = update_coupon_request_dto.model_fields_set
        merged = {
            field_name: getattr(update_coupon_request_dto, field_name) if field_name in supplied else current[field_name]
            for field_name in (
                "coupon_name",
                "coupon_description",
                "discount_type",
                "discount_value",
                "min_order_amount",
                "is_active",
            )
        }
        # Cross-field check that only makes sense post-merge: DTO-level
        # validation can enforce this when both fields arrive together in
        # one request, but not when only one of the two is being updated
        # against the other's already-stored value.
        if merged["discount_type"] == "percentage" and merged["discount_value"] > 100:
            raise InvalidCouponError("A percentage discount_value cannot exceed 100.")

        was_updated = self.coupon_persistence.update_coupon(
            vstitch_coupon_id,
            merged["coupon_name"],
            merged["coupon_description"],
            merged["discount_type"],
            merged["discount_value"],
            merged["min_order_amount"],
            merged["is_active"],
            f"admin:{admin_username}",
        )
        if not was_updated:
            raise ValueError(f"Coupon {vstitch_coupon_id} was not found.")
        return self.get_coupon(vstitch_coupon_id)

    # --- Customer-facing ------------------------------------------------

    def list_available_coupons(self, order_amount):
        """Price-based selection: only IsActive coupons whose
        MinOrderAmount the given order_amount already meets - see
        list_active_coupons_for_amount's own comment for why this is
        always computed fresh, never cached."""
        rows = self.coupon_persistence.list_active_coupons_for_amount(order_amount)
        return AvailableCouponsResponseDTO(
            items=[
                AvailableCouponDTO(
                    coupon_code=row["coupon_code"],
                    coupon_name=row["coupon_name"],
                    coupon_description=row["coupon_description"],
                    discount_type=row["discount_type"],
                    discount_value=row["discount_value"],
                    min_order_amount=row["min_order_amount"],
                )
                for row in rows
            ]
        )

    def apply_coupon(self, apply_coupon_request_dto):
        """Re-validates everything server-side at apply time - a coupon
        being visible in an earlier GET /coupons response (or a code typed
        in manually) is never trusted on its own; IsActive and
        MinOrderAmount are both re-checked against the live row here."""
        coupon = self.coupon_persistence.get_coupon_by_code(apply_coupon_request_dto.coupon_code)
        if coupon is None:
            raise CouponNotFoundError("Invalid coupon code.")
        if not coupon["is_active"]:
            raise ValueError("This coupon is no longer active.")
        if apply_coupon_request_dto.order_amount < coupon["min_order_amount"]:
            raise ValueError(f"This coupon requires a minimum order of {coupon['min_order_amount']:.2f}.")

        order_amount = apply_coupon_request_dto.order_amount
        if coupon["discount_type"] == "percentage":
            discount_amount = order_amount * coupon["discount_value"] / 100
        else:
            # A flat discount is capped at the order total itself - never
            # discount past zero.
            discount_amount = min(coupon["discount_value"], order_amount)
        discount_amount = round(discount_amount, DISCOUNT_ROUNDING_PLACES)
        final_amount = round(order_amount - discount_amount, DISCOUNT_ROUNDING_PLACES)

        return ApplyCouponResponseDTO(
            coupon_code=coupon["coupon_code"],
            discount_amount=discount_amount,
            final_amount=final_amount,
            message="Coupon applied successfully.",
        )

    @staticmethod
    def _to_coupon_dto(row):
        return CouponResponseDTO(
            vstitch_coupon_id=row["vstitch_coupon_id"],
            coupon_name=row["coupon_name"],
            coupon_code=row["coupon_code"],
            coupon_description=row["coupon_description"],
            discount_type=row["discount_type"],
            discount_value=row["discount_value"],
            min_order_amount=row["min_order_amount"],
            is_active=row["is_active"],
        )
