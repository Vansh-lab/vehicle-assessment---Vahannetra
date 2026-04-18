from __future__ import annotations

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
        _ = (data, content_type)
        return StorageObject(key=key, url=f"s3://{self.bucket}/{key}")

    async def presigned_get_url(self, key: str, expires_seconds: int = 3600) -> str:
        _ = expires_seconds
        return f"s3://{self.bucket}/{key}"
