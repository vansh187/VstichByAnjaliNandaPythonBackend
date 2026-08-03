# Marks the notification as high-importance at the transport level - a
# mailto: link (the previous, frontend-only fallback) can only pre-fill
# to/subject/body and has no way to set real email headers; these can only
# be set by whatever actually sends the message, which is the whole reason
# this endpoint exists server-side. Exact header set per the spec - mail
# clients vary in which of these they honor, so all three are sent.
HIGH_PRIORITY_EMAIL_HEADERS = {
    "Importance": "high",
    "X-Priority": "1",
    "X-MSMail-Priority": "High",
}


def build_customization_interest_email(name, phone, email):
    """Returns (subject, plain_text_body) for the admin "someone wants a
    custom outfit" notification - plain text, not HTML, matching the exact
    copy in the spec. `name` is assumed already validated against control
    characters by CreateCustomizationInterestDTO (it lands directly in the
    Subject line below), so no further escaping happens here - this
    function is a pure formatter, not a second validation layer.
    """
    subject = f"Customization Required By {name}"
    body = (
        "A customer has requested a custom outfit through the VStitch website.\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Phone: {phone}\n\n"
        "Please reach out to them as soon as possible to discuss their requirements.\n\n"
        "— Sent from the VStitch website"
    )
    return subject, body
