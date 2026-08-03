from vstitchServices.customizationInterestEmailTemplate import (
    HIGH_PRIORITY_EMAIL_HEADERS,
    build_customization_interest_email,
)


def test_subject_includes_name():
    subject, _body = build_customization_interest_email("Anjali Sharma", "+919876543210", "anjali@example.com")
    assert subject == "Customization Required By Anjali Sharma"


def test_body_matches_spec_content():
    _subject, body = build_customization_interest_email("Anjali Sharma", "+919876543210", "anjali@example.com")
    assert "Name: Anjali Sharma" in body
    assert "Email: anjali@example.com" in body
    assert "Phone: +919876543210" in body
    assert "Please reach out to them as soon as possible" in body
    assert body.startswith("A customer has requested a custom outfit through the VStitch website.")


def test_high_priority_headers_present():
    assert HIGH_PRIORITY_EMAIL_HEADERS["Importance"] == "high"
    assert HIGH_PRIORITY_EMAIL_HEADERS["X-Priority"] == "1"
    assert HIGH_PRIORITY_EMAIL_HEADERS["X-MSMail-Priority"] == "High"
