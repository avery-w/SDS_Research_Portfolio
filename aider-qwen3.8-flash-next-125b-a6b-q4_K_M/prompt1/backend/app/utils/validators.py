import re


def validate_zip(zip_code: str) -> bool:
    return bool(re.match(r"^\d{5}(-\d{4})?$", zip_code))


def validate_phone(phone: str) -> bool:
    return bool(re.match(r"^\+?1?\d{10,15}$", phone))


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")
