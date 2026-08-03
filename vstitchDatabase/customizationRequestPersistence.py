from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader

_CREATE_COLUMN_NAMES = (
    "vstitch_customization_request_id",
    "vstitch_product_id",
    "vstitch_product_variant_id",
    "status",
    "created_at",
)

_LIST_COLUMN_NAMES = (
    "vstitch_customization_request_id",
    "vstitch_product_id",
    "vstitch_product_variant_id",
    "product_name",
    "size",
    "color",
    "customer_name",
    "customer_phone",
    "bust_in",
    "waist_in",
    "hips_in",
    "shoulder_in",
    "sleeve_length_in",
    "dress_length_in",
    "notes",
    "status",
    "created_at",
)


class CustomizationRequestPersistence:
    """Database logic backing the bespoke-measurements ("Request bespoke
    measurements") customization requests, against VStitch_CustomizationRequests.
    """

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("customization_queries.yaml")

    def variant_belongs_to_product(self, vstitch_product_id, vstitch_product_variant_id):
        """True if vstitch_product_variant_id both exists and belongs to
        vstitch_product_id - the single check that covers every "not found"
        corner case (unknown product, unknown variant, or a real variant
        belonging to a *different* product) with one round trip.
        """
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("variant_belongs_to_product"),
                    {
                        "vstitch_product_id": vstitch_product_id,
                        "vstitch_product_variant_id": vstitch_product_variant_id,
                    },
                )
                return cursor.fetchone() is not None

    def create_customization_request(
        self,
        vstitch_product_id,
        vstitch_product_variant_id,
        vstitch_user_id,
        customer_name,
        customer_phone,
        bust_in,
        waist_in,
        hips_in,
        shoulder_in,
        sleeve_length_in,
        dress_length_in,
        notes,
        created_by,
    ):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("insert_customization_request"),
                    {
                        "vstitch_product_id": vstitch_product_id,
                        "vstitch_product_variant_id": vstitch_product_variant_id,
                        "vstitch_user_id": vstitch_user_id,
                        "customer_name": customer_name,
                        "customer_phone": customer_phone,
                        "bust_in": bust_in,
                        "waist_in": waist_in,
                        "hips_in": hips_in,
                        "shoulder_in": shoulder_in,
                        "sleeve_length_in": sleeve_length_in,
                        "dress_length_in": dress_length_in,
                        "notes": notes,
                        "created_by": created_by,
                    },
                )
                row = cursor.fetchone()
            connection.commit()
            return dict(zip(_CREATE_COLUMN_NAMES, row))

    def get_requests_for_user(self, vstitch_user_id):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("get_customization_requests_for_user"),
                    {"vstitch_user_id": vstitch_user_id},
                )
                rows = cursor.fetchall()
            return [dict(zip(_LIST_COLUMN_NAMES, row)) for row in rows]
