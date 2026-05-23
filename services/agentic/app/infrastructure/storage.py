from functools import lru_cache

import boto3
from botocore.config import Config

from app.config import settings


@lru_cache(maxsize=1)
def get_storage_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.rustfs_endpoint,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_default_region,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket(bucket: str | None = None) -> None:
    client = get_storage_client()
    bucket = bucket or settings.rustfs_bucket
    existing = [b["Name"] for b in client.list_buckets().get("Buckets", [])]
    if bucket not in existing:
        client.create_bucket(Bucket=bucket)


def upload_file(key: str, data: bytes, content_type: str = "application/octet-stream", bucket: str | None = None) -> str:
    """Uploads data and returns the storage key (not a URL — served via FastAPI proxy)."""
    client = get_storage_client()
    bucket = bucket or settings.rustfs_bucket
    client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
    return key


def download_file(key: str, bucket: str | None = None) -> bytes:
    client = get_storage_client()
    bucket = bucket or settings.rustfs_bucket
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def delete_file(key: str, bucket: str | None = None) -> None:
    client = get_storage_client()
    bucket = bucket or settings.rustfs_bucket
    client.delete_object(Bucket=bucket, Key=key)
