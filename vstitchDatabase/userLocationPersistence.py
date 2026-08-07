from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader


class UserLocationPersistence:
    """Database logic backing POST /users/location - updates
    Latitude/Longitude/LocationPermissionGranted on an existing
    VStitch_Users row."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("user_queries.yaml")

    def update_location(self, vstitch_user_id, latitude, longitude, updated_by):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("update_user_location"),
                    {
                        "vstitch_user_id": vstitch_user_id,
                        "latitude": latitude,
                        "longitude": longitude,
                        "updated_by": updated_by,
                    },
                )
            connection.commit()
