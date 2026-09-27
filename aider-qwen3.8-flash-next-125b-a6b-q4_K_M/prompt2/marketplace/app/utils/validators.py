import re

def validate_email(email: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email))

def validate_zip(zip_code: str) -> bool:
    return bool(re.match(r"^\d{5}(-\d{4})?$", zip_code))

def validate_price(price) -> bool:
    try:
        return 0 < float(price) < 1_000_000
    except (TypeError, ValueError):
        return False
