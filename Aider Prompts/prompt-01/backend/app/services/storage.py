from typing import BinaryIO
from uuid import uuid4
import boto3
from app.core.config import settings

def upload_product_image(fp: BinaryIO, content_type: str) -> str:
    key = f"products/{uuid4()}.jpg"
    if settings.AWS_S3_BUCKET and settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        s3.upload_fileobj(fp, settings.AWS_S3_BUCKET, key, ExtraArgs={"ACL": "public-read", "ContentType": content_type})
        return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
    # Fallback: store to static/media (ensure directory exists)
    import os
    base = "app/static/media"
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, key.split("/", 1)[1])
    with open(path, "wb") as out:
        out.write(fp.read())
    return f"/static/media/{key.split('/',1)[1]}"
