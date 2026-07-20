import threading
import time


class LocalCacheService:
    """In-process, thread-safe TTL cache for read-heavy, rarely-changing data
    (catalog listings/detail/categories). Lives in this worker's memory only -
    not shared across processes or machines, so a horizontally scaled
    deployment would need a shared cache (e.g. Redis) instead.

    Every method fails open: a cache-layer problem degrades to "treat it as a
    miss" / "skip the write", never to a raised exception, since the cache is
    a speed optimization sitting in front of the database, not a source of
    truth the request depends on.
    """

    def __init__(self):
        self._store = {}
        self._lock = threading.Lock()

    def get(self, key):
        try:
            with self._lock:
                entry = self._store.get(key)
                if entry is None:
                    return None
                expires_at, value = entry
                if expires_at < time.monotonic():
                    del self._store[key]
                    return None
                return value
        except Exception:
            return None

    def set(self, key, value, ttl_seconds):
        try:
            with self._lock:
                self._store[key] = (time.monotonic() + ttl_seconds, value)
        except Exception:
            pass

    def delete(self, key):
        try:
            with self._lock:
                self._store.pop(key, None)
        except Exception:
            pass

    def clear_prefix(self, prefix):
        """Removes every cached entry whose key starts with `prefix`. Used when
        a single write (e.g. a variant selling out) can invalidate an unknown
        number of cached listing pages - cheaper and safer than tracking which
        exact list-query keys included that product."""
        try:
            with self._lock:
                keys_to_remove = [key for key in self._store if key.startswith(prefix)]
                for key in keys_to_remove:
                    del self._store[key]
        except Exception:
            pass


local_cache_service = LocalCacheService()
