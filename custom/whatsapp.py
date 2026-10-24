import re


def whatsapp_digits(value: str) -> str:
    """Return the digits accepted by wa.me for a configured contact number."""
    return re.sub(r"[^0-9]", "", value or "")
