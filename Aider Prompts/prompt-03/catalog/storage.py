import os
import boto3
from botocore.client import Config
from datetime import datetime, timedelta

def generate_presigned_post(key_prefix: str, content_type: str, max_bytes: int = 5 * 1024 * 1024):
    s3 = boto3.client(
        "s3",
        region_name=os.getenv("AWS_S3_REGION_NAME") or os.getenv("AWS_REGION"),
        config=Config(signature_version="s3v4"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    bucket = os.getenv("AWS_S3_BUCKET")
    key = f"{key_prefix}/{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
    conditions = [
        {"bucket": bucket},
        ["content-length-range", 0, max_bytes],
        {"Content-Type": content_type},
    ]
    fields = {"Content-Type": content_type}
    post = s3.generate_presigned_post(Bucket=bucket, Key=key, Fields=fields, Conditions=conditions, ExpiresIn=600)
    return {"url": post["url"], "fields": post["fields"], "key": key}
