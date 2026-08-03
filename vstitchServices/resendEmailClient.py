import os

import requests

RESEND_API_URL = "https://api.resend.com/emails"
RESEND_REQUEST_TIMEOUT_SECONDS = 10


class ResendEmailClient:
    """Thin wrapper around Resend's HTTP API - the only place email
    credentials are read from the environment and the only place Resend's
    API is touched directly, same shape as RazorpayClient/ShiprocketClient
    for their respective providers.
    """

    def __init__(self):
        self.api_key = os.getenv("RESEND_API_KEY")
        self.from_email = os.getenv("VSTITCH_RESEND_EMAIL")
        if not self.api_key:
            raise ValueError("RESEND_API_KEY is not configured in the environment.")
        if not self.from_email:
            raise ValueError("VSTITCH_RESEND_EMAIL is not configured in the environment.")

    def send_email(self, to_email, subject, html_body, attachments=None):
        """Sends one HTML email. `attachments`, if given, is a list of
        {"filename": ..., "content": <base64-encoded bytes>} dicts - Resend's
        own attachment shape. Raises requests.HTTPError/RequestException on
        failure rather than swallowing it - the caller (OrderEmailService)
        is what decides a send failure must never propagate up into the
        order/payment flow, not this client.
        """
        payload = {
            "from": self.from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }
        if attachments:
            payload["attachments"] = attachments

        response = requests.post(
            RESEND_API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=RESEND_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
