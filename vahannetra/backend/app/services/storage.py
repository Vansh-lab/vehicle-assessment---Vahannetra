from __future__ import annotations

from pathlib import Path

from vahannetra.backend.app.core.settings import settings


class LocalArtifactStorage:
    def __init__(self) -> None:
        self.root = settings.artifacts_root
        self.root.mkdir(parents=True, exist_ok=True)

    async def upload_bytes(self, key: str, data: bytes) -> str:
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return key


storage_service = LocalArtifactStorage()
