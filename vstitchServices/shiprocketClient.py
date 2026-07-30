import os
from urllib.parse import quote

import requests

from vstitchServices.localCacheService import local_cache_service

SHIPROCKET_BASE_URL = "https://apiv2.shiprocket.in/v1/external"
SHIPROCKET_REQUEST_TIMEOUT_SECONDS = 10
SHIPROCKET_TOKEN_CACHE_KEY = "shiprocket:auth_token"
# Shiprocket JWTs are valid 240 hours - cached for less than that so a call
# is never handed a token that's about to expire mid-flight, and refreshed
# here rather than by calling /auth/login on every request, per Shiprocket's
# own integration guidance ("cache it, refresh proactively before expiry").
SHIPROCKET_TOKEN_CACHE_TTL_SECONDS = 216 * 60 * 60


class ShiprocketClient:
    """Thin wrapper around the Shiprocket API - the only place shipment
    credentials are read from the environment and the only place Shiprocket
    is touched directly, so the rest of the app depends on this module's
    interface rather than Shiprocket's.

    The auth token is cached process-wide via local_cache_service (in-process,
    TTL'd) rather than fetched per call or per instance - Shiprocket bills a
    fresh login as a new session and asks integrators not to log in on every
    request. Every authenticated method goes through _request(), which logs
    in only when no cached token exists yet (or Shiprocket itself rejects the
    cached one with a 401) and never raises a raw requests/JSON/HTTP-error
    exception - always a ValueError, so one except clause at any call site
    catches everything this client can throw.
    """

    def __init__(self):
        email = os.getenv("VSTITCH_SHIPMENT_EMAIL")
        password = os.getenv("VSTITCH_SHIPMENT_PASSWORD")
        if not email or not password:
            raise ValueError("VSTITCH_SHIPMENT_EMAIL / VSTITCH_SHIPMENT_PASSWORD are not configured in the environment.")
        self.email = email
        self.password = password
        self.token = local_cache_service.get(SHIPROCKET_TOKEN_CACHE_KEY)

    def login(self):
        """Unconditionally calls Shiprocket's login endpoint and refreshes the
        cached token. Prefer letting _request()/ensure_logged_in() call this
        only when needed - this is for the initial login and for recovering
        from a token Shiprocket itself has rejected.
        """
        try:
            response = requests.post(
                f"{SHIPROCKET_BASE_URL}/auth/login",
                json={"email": self.email, "password": self.password},
                timeout=SHIPROCKET_REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            body = response.json()
        except requests.exceptions.RequestException as request_error:
            raise ValueError(f"Unable to reach Shiprocket to log in: {request_error}") from request_error
        except ValueError as json_error:
            # response.json() raises ValueError (json.JSONDecodeError) on a
            # non-JSON body - re-raise as our own message rather than letting
            # the decode error's cryptic text surface to the caller.
            raise ValueError(f"Shiprocket returned an unreadable login response: {json_error}") from json_error

        token = body.get("token")
        if not token:
            raise ValueError("Shiprocket login did not return a token.")

        self.token = token
        local_cache_service.set(SHIPROCKET_TOKEN_CACHE_KEY, token, SHIPROCKET_TOKEN_CACHE_TTL_SECONDS)
        return token

    def ensure_logged_in(self):
        """Returns a usable token, logging in only if nothing is cached yet."""
        if not self.token:
            self.login()
        return self.token

    def logout(self):
        """Explicitly invalidates the current Shiprocket session. Deliberately
        not called automatically anywhere in this client - the token is meant
        to be cached and reused across requests/processes, not logged out
        after each call. Never raises: this is best-effort session cleanup,
        not something any real work depends on succeeding.
        """
        if not self.token:
            return
        try:
            requests.post(
                f"{SHIPROCKET_BASE_URL}/auth/logout",
                headers=self.auth_header(),
                timeout=SHIPROCKET_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.exceptions.RequestException:
            pass
        finally:
            local_cache_service.delete(SHIPROCKET_TOKEN_CACHE_KEY)
            self.token = None

    def auth_header(self):
        if not self.token:
            raise ValueError("Not logged in to Shiprocket - call login() first.")
        return {"Authorization": f"Bearer {self.token}"}

    def _request(self, method, path, allow_reauth_retry=True, **kwargs):
        """Shared HTTP + error-translation path for every authenticated
        Shiprocket call. On a 401 (the cached token expired/was revoked
        despite our TTL), the cached token is dropped and login is retried
        exactly once before giving up - so a stale cache entry self-heals
        instead of failing every call until the TTL naturally elapses.
        """
        self.ensure_logged_in()
        try:
            response = requests.request(
                method,
                f"{SHIPROCKET_BASE_URL}{path}",
                headers=self.auth_header(),
                timeout=SHIPROCKET_REQUEST_TIMEOUT_SECONDS,
                **kwargs,
            )
            body = response.json() if response.content else {}
        except requests.exceptions.RequestException as request_error:
            raise ValueError(f"Unable to reach Shiprocket ({method} {path}): {request_error}") from request_error
        except ValueError as json_error:
            raise ValueError(f"Shiprocket returned an unreadable response ({method} {path}): {json_error}") from json_error

        if response.status_code == 401 and allow_reauth_retry:
            local_cache_service.delete(SHIPROCKET_TOKEN_CACHE_KEY)
            self.token = None
            return self._request(method, path, allow_reauth_retry=False, **kwargs)

        if not response.ok:
            error_message = body.get("message") if isinstance(body, dict) else None
            raise ValueError(f"Shiprocket rejected {method} {path} (HTTP {response.status_code}): {error_message or body}")

        return body

    # --- Order lifecycle -----------------------------------------------

    def create_order(self, order_payload):
        """POST /orders/create/adhoc"""
        return self._request("POST", "/orders/create/adhoc", json=order_payload)

    def check_serviceability(self, pickup_postcode, delivery_postcode, weight_kg, cash_on_delivery):
        """GET /courier/serviceability/ - delivery ETA / COD availability /
        shipping charge, meant to be called at checkout before payment."""
        return self._request(
            "GET",
            "/courier/serviceability/",
            params={
                "pickup_postcode": pickup_postcode,
                "delivery_postcode": delivery_postcode,
                "weight": weight_kg,
                "cod": 1 if cash_on_delivery else 0,
            },
        )

    def get_pickup_locations(self):
        """GET /settings/company/pickup"""
        return self._request("GET", "/settings/company/pickup")

    def track_order(self, shiprocket_order_id):
        """GET /courier/track?order_id="""
        return self._request("GET", "/courier/track", params={"order_id": shiprocket_order_id})

    def track_by_awb(self, awb_code):
        """GET /courier/track/awb/{awb_code} - unlike track_order (which
        returned an empty shipment_track for a live order during testing),
        this endpoint reliably returns the shipment's current tracking state
        keyed by AWB, so it's the one used for admin-triggered status
        reconciliation (see ShipmentService.sync_order_status_from_shiprocket).
        """
        return self._request("GET", f"/courier/track/awb/{quote(str(awb_code), safe='')}")

    def cancel_orders(self, shiprocket_order_ids):
        """POST /orders/cancel - only works pre-dispatch; once picked up,
        Shiprocket may reject the cancellation and this raises ValueError."""
        return self._request("POST", "/orders/cancel", json={"ids": shiprocket_order_ids})

    def cancel_shipment_awbs(self, awb_codes):
        """POST /orders/cancel/shipment/awbs"""
        return self._request("POST", "/orders/cancel/shipment/awbs", json={"awbs": awb_codes})

    def create_return_order(self, return_order_payload):
        """POST /orders/create/return"""
        return self._request("POST", "/orders/create/return", json=return_order_payload)

    def check_return_serviceability(self, pickup_postcode, delivery_postcode, weight_kg):
        """GET /courier/serviceability/?is_return=1"""
        return self._request(
            "GET",
            "/courier/serviceability/",
            params={
                "pickup_postcode": pickup_postcode,
                "delivery_postcode": delivery_postcode,
                "weight": weight_kg,
                "is_return": 1,
            },
        )

    # --- Fulfillment / ops -----------------------------------------------

    def assign_awb(self, shipment_id):
        """POST /courier/assign/awb"""
        return self._request("POST", "/courier/assign/awb", json={"shipment_id": shipment_id})

    def generate_pickup(self, shipment_ids):
        """POST /courier/generate/pickup"""
        return self._request("POST", "/courier/generate/pickup", json={"shipment_id": shipment_ids})

    def generate_label(self, shipment_ids):
        """POST /courier/generate/label"""
        return self._request("POST", "/courier/generate/label", json={"shipment_id": shipment_ids})

    def generate_manifest(self, shipment_ids):
        """POST /manifests/generate"""
        return self._request("POST", "/manifests/generate", json={"shipment_id": shipment_ids})

    def generate_invoice(self, shiprocket_order_ids):
        """POST /orders/print/invoice"""
        return self._request("POST", "/orders/print/invoice", json={"ids": shiprocket_order_ids})

    def get_ndr_orders(self):
        """GET /ndr/list - verified live against the account this was built
        against; plain GET /ndr 404s on that account, /ndr/list returns 200."""
        return self._request("GET", "/ndr/list")

    def take_ndr_action(self, ndr_action_payload):
        """NOT VERIFIED - live-tested POST/PUT/PATCH /ndr and POST /ndr
        both 404/405 against the account this was built against ("Supported
        methods: GET, HEAD" on /ndr/action). The real mutating NDR-action
        endpoint is something else; don't call this until it's corrected
        against Shiprocket's actual NDR reference or a support-confirmed path.
        """
        raise ValueError(
            "take_ndr_action's endpoint is unverified and known-wrong (see docstring) - "
            "confirm the real path/method with Shiprocket before wiring this up."
        )
