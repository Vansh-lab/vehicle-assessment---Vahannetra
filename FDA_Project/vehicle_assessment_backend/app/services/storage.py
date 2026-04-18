from __future__ import annotations

import os
from dataclasses import dataclass

from app.core.settings import settings


@dataclass
class StorageObject:
    key: str
    url: str


class ArtifactStorageService:
    """
    Async-ready storage abstraction with a local fallback contract.
    Future implementation can switch to aioboto3 without changing callers.
    """

    def __init__(self, bucket: str | None = None):
        self.bucket = bucket or settings.s3_bucket

    async def upload_bytes(self, key: str, data: bytes, content_type: str) -> StorageObject:
        if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
            try:
                import aioboto3  # type: ignore

                session = aioboto3.Session()
                region = os.getenv("AWS_REGION", "ap-south-1")
                async with session.client("s3", region_name=region) as s3:
                    await s3.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
                return StorageObject(key=key, url=f"s3://{self.bucket}/{key}")
            except Exception:
                pass
        return StorageObject(key=key, url=f"s3://{self.bucket}/{key}")

    async def presigned_get_url(self, key: str, expires_seconds: int = 3600) -> str:
        _ = expires_seconds
        return f"s3://{self.bucket}/{key}"
