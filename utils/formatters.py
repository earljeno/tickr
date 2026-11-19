import re
from datetime import datetime, time


def normalize_philippine_phone(phone: str | None) -> str:
    """Normalize a Philippine phone number to 639XXXXXXXXX digits."""
    if not phone:
        return ""

    digits = re.sub(r"\D+", "", str(phone))
    digits = re.sub(r"^00", "", digits)

    if digits == "63":
        return ""

    if digits.startswith("63"):
        pass
    elif digits.startswith("0"):
        digits = "63" + digits[1:]
    else:
        digits = "63" + digits

    return "" if digits == "63" else digits


def format_philippine_phone(phone: str | None) -> str:
    """Format a Philippine phone number into '+63 XXX XXX XXXX' display format."""
    digits = normalize_philippine_phone(phone)
    if not digits:
        return ""

    rest = digits[2:]
    if len(rest) == 10:
        return f"+63 {rest[:3]} {rest[3:6]} {rest[6:]}"
    if len(rest) == 9:
        return f"+63 {rest[:1]} {rest[1:5]} {rest[5:]}"
    if len(rest) == 8:
        return f"+63 {rest[:3]} {rest[3:]}"
    if len(rest) == 7:
        return f"+63 {rest[:3]} {rest[3:]}"
    return f"+{digits}"


def parse_time(value: str | None) -> time | None:
    """Convert 'HH:MM' string to Python time object or None."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%H:%M").time()
    except (ValueError, AttributeError):
        return None
