import re

EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
URL_RE = re.compile(
    r"^https?://"
    r"(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}"
    r"(?:/[^\s]*)?$"
)


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))


def is_valid_url(url: str) -> bool:
    return bool(URL_RE.match(url))


def sanitize_string(value: str, max_length: int = 5000) -> str:
    """Strip whitespace and truncate to max_length."""
    return value.strip()[:max_length]
