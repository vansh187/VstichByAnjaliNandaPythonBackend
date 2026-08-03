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

    def send_email(self, to_email, subject, html_body=None, text_body=None, attachments=None, headers=None):
        """Sends one email. Exactly one of html_body/text_body is the usual
        case (Resend accepts either or both), so both are optional here
        rather than html_body being required - the plain-text
        customization-interest notification has no HTML version at all.
        Raises ValueError if neither is given, since Resend itself would
        otherwise reject the request with a less obvious error.

        `attachments`, if given, is a list of {"filename": ...,
        "content": <base64-encoded bytes>} dicts - Resend's own attachment
        shape. `headers`, if given, is a dict of extra transport headers
        (e.g. {"Importance": "high"}) - passed through as-is, Resend's own
        "headers" field.

        Raises requests.HTTPError/RequestException on failure rather than
        swallowing it - it's each caller's own decision whether a send
        failure may propagate (e.g. CustomizationInterestService, where
        sending *is* the endpoint's deliverable) or must never do so (e.g.
        OrderEmailService, where the order/payment flow must never fail
        because of an email problem) - not this client's to make.
        """
        if not html_body and not text_body:
            raise ValueError("send_email requires html_body and/or text_body.")

        payload = {
            "from": self.from_email,
            "to": [to_email],
            "subject": subject,
        }
        if html_body:
            payload["html"] = html_body
        if text_body:
            payload["text"] = text_body
        if attachments:
            payload["attachments"] = attachments
        if headers:
            payload["headers"] = headers

        response = requests.post(
            RESEND_API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=RESEND_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
