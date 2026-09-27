import boto3
from botocore.config import Config
from app.config import settings


class StorageService:
    def __init__(self):
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            config=Config(signature_version="s3v4"),
        )
        self.bucket = settings.AWS_S3_BUCKET

    def generate_presigned_upload_url(self, key: str, content_type: str = "image/jpeg") -> str:
        return self.s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=3600,
        )

    def get_public_url(self, key: str) -> str:
        return f"https://{self.bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
