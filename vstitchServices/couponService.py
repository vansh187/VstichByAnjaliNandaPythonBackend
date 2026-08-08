from datetime import datetime

from vstitchDatabase.couponPersistence import CouponPersistence, InvalidCouponError
from vstitchDTO.applyCouponDTO import ApplyCouponResponseDTO
from vstitchDTO.couponResponseDTO import AvailableCouponDTO, AvailableCouponsResponseDTO, CouponResponseDTO

# Percentage discounts are rounded to paise/cents; a flat discount is
# already an exact currency amount and needs no rounding.
DISCOUNT_ROUNDING_PLACES = 2

# UpdateCouponRequestDTO fields CouponService.update_coupon merges onto
# the current row - everything except coupon_code/valid_from/used_count,
# none of which are ever updated through this endpoint (see
# UpdateCouponRequestDTO's own comment).
UPDATABLE_COUPON_FIELDS = (
    "discount_type",
    "discount_value",
    "min_order_amount",
    "max_discount_amount",
    "usage_limit",
    "valid_until",
    "is_active",
)


class CouponNotFoundError(ValueError):
    """No coupon exists with this code - mapped to 404, distinct from the
    plain ValueError below (inactive/threshold-not-met/expired/exhausted),
    which is a 409: the coupon *exists*, just can't be applied right now."""


class CouponService:
    """Business logic for coupon CRUD (admin), the public price-based
    coupon list, and the checkout apply flow."""

    def __init__(self):
        self.coupon_persistence = CouponPersistence()

    # --- Admin --------------------------------------------------------

    def create_coupon(self, create_coupon_request_dto, admin_username):
        row = self.coupon_persistence.create_coupon(
            create_coupon_request_dto.coupon_code,
            create_coupon_request_dto.discount_type,
            create_coupon_request_dto.discount_value,
            create_coupon_request_dto.min_order_amount,
            create_coupon_request_dto.max_discount_amount,
            create_coupon_request_dto.usage_limit,
            create_coupon_request_dto.valid_until,
            f"admin:{admin_username}",
        )
        return self._to_coupon_dto(row)

    def get_coupon(self, vstitch_coupon_id):
        row = self.coupon_persistence.get_coupon_by_id(vstitch_coupon_id)
        if row is None:
            raise ValueError(f"Coupon {vstitch_coupon_id} was not found.")
        return self._to_coupon_dto(row)

    def list_coupons_admin(self):
        """Every coupon, active and inactive, newest first - a bare list,
        no pagination wrapper, per the admin contract's own response
        shape."""
        rows = self.coupon_persistence.list_coupons_admin()
        return [self._to_coupon_dto(row) for row in rows]

    def update_coupon(self, vstitch_coupon_id, update_coupon_request_dto, admin_username):
        current = self.coupon_persistence.get_coupon_by_id(vstitch_coupon_id)
        if current is None:
            raise ValueError(f"Coupon {vstitch_coupon_id} was not found.")

        supplied = update_coupon_request_dto.model_fields_set
        merged = {
            field_name: getattr(update_coupon_request_dto, field_name) if field_name in supplied else current[field_name]
            for field_name in UPDATABLE_COUPON_FIELDS
        }
        # Cross-field check that only makes sense post-merge: DTO-level
        # validation can enforce this when both fields arrive together in
        # one request, but not when only one of the two is being updated
        # against the other's already-stored value.
        if merged["discount_type"] == "percentage" and merged["discount_value"] > 100:
            raise InvalidCouponError("A percentage discount_value cannot exceed 100.")

        was_updated = self.coupon_persistence.update_coupon(
            vstitch_coupon_id,
            merged["discount_type"],
            merged["discount_value"],
            merged["min_order_amount"],
            merged["max_discount_amount"],
            merged["usage_limit"],
            merged["valid_until"],
            merged["is_active"],
            f"admin:{admin_username}",
        )
        if not was_updated:
            raise ValueError(f"Coupon {vstitch_coupon_id} was not found.")
        return self.get_coupon(vstitch_coupon_id)

    # --- Customer-facing ------------------------------------------------

    def list_available_coupons(self, order_amount):
        """Price-based selection: only IsActive coupons whose
        MinOrderAmount the given order_amount already meets, that are
        inside their valid-from/until window, and haven't hit their usage
        limit - see list_active_coupons_for_amount's own comment for why
        this is always computed fresh, never cached."""
        rows = self.coupon_persistence.list_active_coupons_for_amount(order_amount)
        return AvailableCouponsResponseDTO(
            items=[
                AvailableCouponDTO(
                    coupon_code=row["coupon_code"],
                    discount_type=row["discount_type"],
                    discount_value=row["discount_value"],
                    min_order_amount=row["min_order_amount"],
                    max_discount_amount=row["max_discount_amount"],
                )
                for row in rows
            ]
        )

    def apply_coupon(self, apply_coupon_request_dto):
        """Re-validates everything server-side at apply time - a coupon
        being visible in an earlier GET /coupons response (or a code typed
        in manually) is never trusted on its own. Does NOT increment
        UsedCount: this is a preview/validation step a shopper can call
        any number of times without ever completing an order - real
        redemption tracking belongs in the checkout/order-completion flow
        (see CouponPersistence.increment_used_count)."""
        coupon = self.coupon_persistence.get_coupon_by_code(apply_coupon_request_dto.coupon_code)
        if coupon is None:
            raise CouponNotFoundError("Invalid coupon code.")
        if not coupon["is_active"]:
            raise ValueError("This coupon is no longer active.")

        now = datetime.now()
        if coupon["valid_from"] > now:
            raise ValueError("This coupon is not active yet.")
        if coupon["valid_until"] is not None and coupon["valid_until"] < now:
            raise ValueError("This coupon has expired.")
        if coupon["usage_limit"] is not None and coupon["used_count"] >= coupon["usage_limit"]:
            raise ValueError("This coupon has reached its usage limit.")

        if coupon["min_order_amount"] is not None and apply_coupon_request_dto.order_amount < coupon["min_order_amount"]:
            raise ValueError(f"This coupon requires a minimum order of {coupon['min_order_amount']:.2f}.")

        order_amount = apply_coupon_request_dto.order_amount
        if coupon["discount_type"] == "percentage":
            discount_amount = order_amount * coupon["discount_value"] / 100
            if coupon["max_discount_amount"] is not None:
                discount_amount = min(discount_amount, coupon["max_discount_amount"])
        else:
            # A flat discount is capped at the order total itself - never
            # discount past zero. max_discount_amount is irrelevant here:
            # discount_value already IS the absolute currency amount.
            discount_amount = coupon["discount_value"]
        # Never discount past the order total itself, regardless of type.
        discount_amount = min(discount_amount, order_amount)
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
            coupon_code=row["coupon_code"],
            discount_type=row["discount_type"],
            discount_value=row["discount_value"],
            min_order_amount=row["min_order_amount"],
            max_discount_amount=row["max_discount_amount"],
            usage_limit=row["usage_limit"],
            used_count=row["used_count"],
            valid_from=row["valid_from"],
            valid_until=row["valid_until"],
            is_active=row["is_active"],
            created_date=row["created_date"],
        )
