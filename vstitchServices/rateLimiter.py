from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared Limiter instance - imported both by main.py (to register it on the
# app + wire the 429 handler/middleware) and by the individual login/signup
# API modules (to decorate their specific handlers with a tighter limit).
# Keyed by remote IP; in-memory storage, so limits are per-process - same
# accepted trade-off as localCacheService's in-process-only cache. Revisit
# with a Redis-backed store only if Render ever runs more than one
# worker/instance.
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
