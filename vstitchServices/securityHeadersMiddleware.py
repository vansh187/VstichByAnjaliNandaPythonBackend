from starlette.middleware.base import BaseHTTPMiddleware

# Applied to every response - this is a pure JSON API for every route except
# FastAPI's own auto-generated docs pages, so a maximally restrictive CSP is
# safe by default and doesn't need per-route tuning the way a page-serving
# app's would.
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy": "default-src 'none'",
}

# /docs and /redoc serve HTML that loads Swagger UI/ReDoc's JS+CSS from
# jsdelivr and then fetches /openapi.json client-side - default-src 'none'
# silently blocks all of that, rendering an empty page. 'unsafe-inline' on
# script-src is needed because FastAPI's stock docs HTML initializes
# SwaggerUIBundle/Redoc via an inline <script> tag with no nonce support.
DOCS_PATHS = {"/docs", "/redoc", "/openapi.json"}
DOCS_CONTENT_SECURITY_POLICY = (
    "default-src 'none'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "connect-src 'self'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard hardening headers to every response - defense-in-depth
    against clickjacking, MIME-sniffing, and protocol-downgrade attacks.
    None of this replaces proper auth/input-validation, it just removes the
    "free" attack surface a browser-facing API leaves open by omission.
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        for header_name, header_value in SECURITY_HEADERS.items():
            response.headers[header_name] = header_value
        if request.url.path in DOCS_PATHS:
            response.headers["Content-Security-Policy"] = DOCS_CONTENT_SECURITY_POLICY
        return response
