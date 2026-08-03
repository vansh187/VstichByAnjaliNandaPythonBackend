from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader


class CustomizationInterestPersistence:
    """Database logic backing VSTITCH_CUSTOMIZED_USER - leads captured from
    the VStitch AI widget's "Need a Custom Outfit?" form.
    """

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("customization_interest_queries.yaml")

    def save_lead(self, customer_name, customer_phone, customer_email, created_by):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("insert_customization_interest_lead"),
                    {
                        "customer_name": customer_name,
                        "customer_phone": customer_phone,
                        "customer_email": customer_email,
                        "created_by": created_by,
                    },
                )
                vstitch_customized_user_id = cursor.fetchone()[0]
            connection.commit()
            return vstitch_customized_user_id
