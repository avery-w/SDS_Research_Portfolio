import re
from html import escape


def sanitize_text(value, max_length=255):
    if value is None:
        return ""
    text = str(value).strip()
    text = escape(text)
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    if max_length and len(text) > max_length:
        text = text[:max_length]
    return text


def sanitize_search(value, max_length=100):
    text = sanitize_text(value, max_length=max_length)
    return text


def sanitize_filename(name):
    if not name:
        return ""
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    name = name.strip("._")
    return name[:120]


def sanitize_email(value):
    if value is None:
        return ""
    return sanitize_text(value.lower(), max_length=150)
