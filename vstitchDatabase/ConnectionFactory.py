import os

import psycopg2
import psycopg2.pool
from dotenv import load_dotenv

load_dotenv()


class ConnectionFactory:
    """Owns a pooled connection to the Postgres database configured in .env.

    Uses ThreadedConnectionPool, not SimpleConnectionPool: FastAPI runs sync
    `def` route handlers on a worker thread pool, so concurrent requests can
    call get_connection()/release_connection() from different threads at the
    same time. SimpleConnectionPool is documented as unsafe to share across
    threads and would corrupt its internal state under that load.
    """

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL is not configured in the environment.")
        self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
            1, 10, dsn=self.database_url
        )

    def get_connection(self):
        return self.connection_pool.getconn()

    def release_connection(self, connection):
        self.connection_pool.putconn(connection)

    def close_all_connections(self):
        self.connection_pool.closeall()


connection_factory = ConnectionFactory()
