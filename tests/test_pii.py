from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_identity_and_payment_numbers() -> None:
    for value, kind in (("123456789012", "CCCD"), ("4111 1111 1111 1111", "CREDIT_CARD"), ("4111111111111111", "CREDIT_CARD")):
        assert scrub_text(value) == f"[REDACTED_{kind}]"


def test_scrub_nested_event_and_metadata() -> None:
    from app.logging_config import scrub_event
    event = {"session_id": "student+test@example.test", "payload": {"nested": ["0901234567", {"card": "4111-1111-1111-1111"}]}}
    safe = scrub_event(None, "info", event)
    assert safe["session_id"] == "[REDACTED_EMAIL]"
    assert safe["payload"]["nested"][0] == "[REDACTED_PHONE_VN]"
    assert safe["payload"]["nested"][1]["card"] == "[REDACTED_CREDIT_CARD]"
