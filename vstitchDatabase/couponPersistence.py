import psycopg2.errors

from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader
from vstitchDatabase.uniqueConstraintError import translate_unique_violation

COUPON_COLUMNS = (
    "vstitch_coupon_id",
    "coupon_name",
    "coupon_code",
    "coupon_description",
    "discount_type",
    "discount_value",
    "min_order_amount",
    "is_active",
)

COUPON_UNIQUE_CONSTRAINT_MESSAGES = {
    "uq_vstitch_coupons_code": "A coupon with this code already exists.",
}

# Both DB-level CHECK constraints (ck_vstitch_coupons_discount_value,
# ck_vstitch_coupons_percentage_range) surface the same class of error to a
# caller - "the discount value/type combination is invalid" - so both map
# to this one message rather than trying to distinguish which CHECK fired
# from the exception alone.
INVALID_DISCOUNT_MESSAGE = "discount_value must be positive, and a percentage discount_value cannot exceed 100."


class InvalidCouponError(ValueError):
    """A coupon business-rule violation that isn't "not found" or
    "duplicate code" - the discount value/type combination itself is
    invalid (DB CHECK-constraint violation, or CouponService.update_coupon's
    own post-merge check). A ValueError subclass, same shape as
    UniqueConstraintError, so the admin API layer can map this to 422
    specifically instead of the plain-ValueError "not found" -> 404 case."""


def _row_to_coupon_dict(row):
    """psycopg2 returns NUMERIC columns (DiscountValue, MinOrderAmount) as
    decimal.Decimal, not float - CouponService.apply_coupon does plain
    arithmetic (order_amount * discount_value / 100) against these using
    the float it received from ApplyCouponRequestDTO, and float `op`
    Decimal raises TypeError for every arithmetic operator (unlike
    comparisons, which work fine between the two - the reason this only
    ever broke the *successful* apply path, not the rejection paths, when
    it first shipped). Casting to float once, here, at the single place
    every coupon row is turned into a dict, means every caller - present
    and future - gets a plain float and can never hit this again.
    """
    coupon = dict(zip(COUPON_COLUMNS, row))
    coupon["discount_value"] = float(coupon["discount_value"])
    coupon["min_order_amount"] = float(coupon["min_order_amount"])
    return coupon


class CouponPersistence:
    """Database logic backing VSTITCH_COUPONS - admin CRUD, the public
    price-based coupon list, and code lookup for the checkout apply flow."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("coupon_queries.yaml")

    def create_coupon(
        self,
        coupon_name,
        coupon_code,
        coupon_description,
        discount_type,
        discount_value,
        min_order_amount,
        is_active,
        created_by,
    ):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                try:
                    cursor.execute(
                        self.query_loader.get_query("insert_coupon"),
                        (
                            coupon_name,
                            coupon_code,
                            coupon_description,
                            discount_type,
                            discount_value,
                            min_order_amount,
                            is_active,
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

    def list_coupons_admin(self, after_id, limit_plus_one):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("list_coupons_admin"),
                    {"after_id": after_id, "limit_plus_one": limit_plus_one},
                )
                rows = cursor.fetchall()
            return [_row_to_coupon_dict(row) for row in rows]

    def list_active_coupons_for_amount(self, order_amount):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("list_active_coupons_for_amount"), (order_amount,))
                rows = cursor.fetchall()
            return [_row_to_coupon_dict(row) for row in rows]

    def update_coupon(
        self,
        vstitch_coupon_id,
        coupon_name,
        coupon_description,
        discount_type,
        discount_value,
        min_order_amount,
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
                            "coupon_name": coupon_name,
                            "coupon_description": coupon_description,
                            "discount_type": discount_type,
                            "discount_value": discount_value,
                            "min_order_amount": min_order_amount,
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
