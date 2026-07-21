from starlette.middleware.base import BaseHTTPMiddleware

# Applied to every response - this is a pure JSON API (no HTML/JS is ever
# served), so a maximally restrictive CSP is safe by default and doesn't
# need per-route tuning the way a page-serving app's would.
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy": "default-src 'none'",
}


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
        return response
