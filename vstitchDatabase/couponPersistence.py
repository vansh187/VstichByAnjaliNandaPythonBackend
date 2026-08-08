import psycopg2.errors

from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader
from vstitchDatabase.uniqueConstraintError import translate_unique_violation

COUPON_COLUMNS = (
    "vstitch_coupon_id",
    "coupon_code",
    "discount_type",
    "discount_value",
    "min_order_amount",
    "max_discount_amount",
    "usage_limit",
    "used_count",
    "valid_from",
    "valid_until",
    "is_active",
    "created_date",
)

# Nullable NUMERIC columns - cast to float only when present, unlike
# discount_value (always required, cast unconditionally below).
NULLABLE_NUMERIC_COLUMNS = ("min_order_amount", "max_discount_amount")

COUPON_UNIQUE_CONSTRAINT_MESSAGES = {
    "uq_vstitch_coupons_code": "A coupon with this code already exists.",
}

# The several DB-level CHECK constraints on VSTITCH_COUPONS
# (discount_value, percentage_range, min_order_amount, max_discount_amount,
# usage_limit, used_count, valid_window) all surface the same class of
# error to a caller - "one of the numeric/date fields is invalid" - so all
# map to this one message rather than trying to distinguish which CHECK
# fired from the exception alone.
INVALID_DISCOUNT_MESSAGE = (
    "One or more coupon fields are invalid: discount_value must be positive (and ≤ 100 for a percentage "
    "coupon), min_order_amount/max_discount_amount/usage_limit/used_count must not be negative, and "
    "valid_until (if set) must not be before valid_from."
)


class InvalidCouponError(ValueError):
    """A coupon business-rule violation that isn't "not found" or
    "duplicate code" - one of the numeric/date fields itself is invalid
    (DB CHECK-constraint violation, or CouponService.update_coupon's own
    post-merge percentage check). A ValueError subclass, same shape as
    UniqueConstraintError, so the admin API layer can map this to 422
    specifically instead of the plain-ValueError "not found" -> 404 case."""


def _row_to_coupon_dict(row):
    """psycopg2 returns NUMERIC columns as decimal.Decimal, not float -
    CouponService does plain arithmetic (order_amount * discount_value /
    100) against these using the float it received from request DTOs, and
    float `op` Decimal raises TypeError for every arithmetic operator
    (unlike comparisons, which work fine between the two). Casting to
    float once, here, at the single place every coupon row is turned into
    a dict, means every caller - present and future - gets a plain float
    (or None, for the nullable numeric columns) and can never hit this."""
    coupon = dict(zip(COUPON_COLUMNS, row))
    coupon["discount_value"] = float(coupon["discount_value"])
    for column_name in NULLABLE_NUMERIC_COLUMNS:
        if coupon[column_name] is not None:
            coupon[column_name] = float(coupon[column_name])
    return coupon


class CouponPersistence:
    """Database logic backing VSTITCH_COUPONS - admin CRUD, the public
    price-based coupon list, and code lookup for the checkout apply flow."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("coupon_queries.yaml")

    def create_coupon(
        self,
        coupon_code,
        discount_type,
        discount_value,
        min_order_amount,
        max_discount_amount,
        usage_limit,
        valid_until,
        created_by,
    ):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                try:
                    cursor.execute(
                        self.query_loader.get_query("insert_coupon"),
                        (
                            coupon_code,
                            discount_type,
                            discount_value,
                            min_order_amount,
                            max_discount_amount,
                            usage_limit,
                            valid_until,
                            created_by,
                        ),
                    )
                    vstitch_coupon_id = cursor.fetchone()[0]
                except psycopg2.errors.UniqueViolation as unique_violation:
                    connection.rollback()
                    raise translate_unique_violation(
                        unique_violation, COUPON_UNIQUE_CONSTRAINT_MESSAGES, "A coupon with conflicting details already exists."
                    ) from unique_violation
                except psycopg2.errors.CheckViolation as check_violation:
                    connection.rollback()
                    raise InvalidCouponError(INVALID_DISCOUNT_MESSAGE) from check_violation
            connection.commit()
        return self.get_coupon_by_id(vstitch_coupon_id)

    def get_coupon_by_id(self, vstitch_coupon_id):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("get_coupon_by_id"), (vstitch_coupon_id,))
                row = cursor.fetchone()
            return _row_to_coupon_dict(row) if row is not None else None

    def get_coupon_by_code(self, coupon_code):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("get_coupon_by_code"), (coupon_code,))
                row = cursor.fetchone()
            return _row_to_coupon_dict(row) if row is not None else None

    def list_coupons_admin(self):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("list_coupons_admin"))
                rows = cursor.fetchall()
            return [_row_to_coupon_dict(row) for row in rows]

    def list_active_coupons_for_amount(self, order_amount):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("list_active_coupons_for_amount"), {"order_amount": order_amount}
                )
                rows = cursor.fetchall()
            return [_row_to_coupon_dict(row) for row in rows]

    def update_coupon(
        self,
        vstitch_coupon_id,
        discount_type,
        discount_value,
        min_order_amount,
        max_discount_amount,
        usage_limit,
        valid_until,
        is_active,
        updated_by,
    ):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                try:
                    cursor.execute(
                        self.query_loader.get_query("update_coupon"),
                        {
                            "vstitch_coupon_id": vstitch_coupon_id,
                            "discount_type": discount_type,
                            "discount_value": discount_value,
                            "min_order_amount": min_order_amount,
                            "max_discount_amount": max_discount_amount,
                            "usage_limit": usage_limit,
                            "valid_until": valid_until,
                            "is_active": is_active,
                            "updated_by": updated_by,
                        },
                    )
                    row = cursor.fetchone()
                except psycopg2.errors.CheckViolation as check_violation:
                    connection.rollback()
                    raise InvalidCouponError(INVALID_DISCOUNT_MESSAGE) from check_violation
            connection.commit()
            return row is not None

    def increment_used_count(self, vstitch_coupon_id, updated_by):
        """Not called anywhere yet - see increment_used_count's comment in
        coupon_queries.yaml. Returns the new UsedCount, or None if the
        coupon didn't exist or was already at its UsageLimit (the UPDATE
        matched zero rows)."""
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("increment_used_count"),
                    {"vstitch_coupon_id": vstitch_coupon_id, "updated_by": updated_by},
                )
                row = cursor.fetchone()
            connection.commit()
            return row[0] if row is not None else None
