import io
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.config import get_settings

settings = get_settings()

UPLOAD_DIR = Path("static/uploads")
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def save_product_image(file: UploadFile) -> str:
    """Validate an uploaded image (real content, size, format) and save it. Returns the web path."""
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"Image exceeds {settings.max_upload_mb}MB limit")

    try:
        image = Image.open(io.BytesIO(data))
        image.verify()
        image = Image.open(io.BytesIO(data))  # re-open after verify()
        if image.format not in ALLOWED_FORMATS:
            raise ValueError
    except (UnidentifiedImageError, ValueError):
        raise HTTPException(status_code=400, detail="File is not a valid JPEG/PNG/WEBP image")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = image.format.lower().replace("jpeg", "jpg")
    name = f"{uuid.uuid4().hex}.{ext}"
    dest = UPLOAD_DIR / name
    image.save(dest)
    return f"/static/uploads/{name}"
