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
    return sanitize_text(value, max_length=max_length)


def sanitize_filename(name):
    if not name:
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    cleaned = cleaned.strip("._")
    return cleaned[:120]
