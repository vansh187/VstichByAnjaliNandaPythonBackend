import contextlib
import os
import time

import psycopg2
import psycopg2.pool
from dotenv import load_dotenv

load_dotenv()

CONNECTION_WAIT_TIMEOUT_SECONDS = 5
CONNECTION_RETRY_INTERVAL_SECONDS = 0.05


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
        # minconn == maxconn: ThreadedConnectionPool eagerly opens `minconn`
        # connections in this constructor and only opens the rest lazily, on
        # first demand, under the pool's single internal lock. Establishing a
        # new connection to this Supabase instance measured ~0.9s each, so a
        # cold pool (minconn=1) serializes ~0.9s of connection setup into the
        # request path of whichever concurrent requests are unlucky enough to
        # need a new connection - the request-time cost this cache exists to
        # avoid. Pre-warming all 10 here pays that cost once at startup.
        self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
            10, 10, dsn=self.database_url
        )

    def get_connection(self):
        # ThreadedConnectionPool.getconn() raises PoolError immediately when
        # every connection is checked out - it does not wait. Under a burst of
        # concurrent requests (e.g. many shoppers hitting a listing page at
        # once) that would surface as a raw 500 even though every connection
        # is only held for a few milliseconds. Retry with a short backoff so
        # a transient burst succeeds once a connection frees up, instead of
        # failing the request outright; still raises if genuinely overloaded
        # past CONNECTION_WAIT_TIMEOUT_SECONDS.
        deadline = time.monotonic() + CONNECTION_WAIT_TIMEOUT_SECONDS
        while True:
            try:
                return self.connection_pool.getconn()
            except psycopg2.pool.PoolError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(CONNECTION_RETRY_INTERVAL_SECONDS)

    def release_connection(self, connection, discard=False):
        # discard=True closes the physical connection and drops it from the
        # pool instead of recycling it - used when the connection itself is
        # known-unhealthy (e.g. its own rollback failed), so a broken
        # connection never gets handed to the next, unrelated request. The
        # pool lazily opens a fresh replacement the next time it's needed.
        self.connection_pool.putconn(connection, close=discard)

    def close_all_connections(self):
        self.connection_pool.closeall()

    @contextlib.contextmanager
    def connection(self):
        """Checks out a connection and guarantees correct cleanup on every
        exit path - the single place this logic should live, since every
        persistence method needs the same three guarantees:

        1. On success: release the connection back to the pool as-is.
        2. On a query/business exception: roll back before releasing, so a
           failed query never leaves the connection in Postgres's "aborted
           transaction" state for the *next*, unrelated request that reuses
           it from the pool (that request would otherwise fail immediately
           with InFailedSqlTransaction, for a query it never made).
        3. If the rollback itself fails (the connection is actually broken -
           dropped socket, DB restart mid-request, etc.): discard the
           connection entirely rather than recycling a connection that can't
           even roll back cleanly.
        """
        connection = self.get_connection()
        should_discard = False
        try:
            yield connection
        except Exception:
            try:
                connection.rollback()
            except Exception:
                should_discard = True
            raise
        finally:
            self.release_connection(connection, discard=should_discard)


connection_factory = ConnectionFactory()
