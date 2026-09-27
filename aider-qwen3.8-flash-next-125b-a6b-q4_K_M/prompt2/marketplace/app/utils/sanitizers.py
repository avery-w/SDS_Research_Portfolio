import re
import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

def sanitize_string(value: str) -> str:
    """Strip HTML tags, trim whitespace, limit length."""
    if not isinstance(value, str):
        return ""
    value = re.sub(r"<[^>]+>", "", value)  # strip HTML/script tags
    value = value.strip()
    return value[:500]

def sanitize_search_query(query: str) -> str:
    """Remove SQL/NoSQL injection characters; allow alphanumeric, spaces, hyphens."""
    if not isinstance(query, str):
        return ""
    return re.sub(r"[^a-zA-Z0-9\s\-_.,]", "", query.strip())[:200]

def sanitize_file_path(filename: str) -> str:
    """Use Werkzeug secure_filename; reject path traversal."""
    safe = secure_filename(filename)
    if ".." in safe or "/" in safe or "\\" in safe:
        raise ValueError("Invalid filename")
    return safe

def validate_extension(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def sanitize_quantity(q) -> int:
    try:
        val = int(q)
        return max(1, min(val, 999))
    except (TypeError, ValueError):
        return 1
