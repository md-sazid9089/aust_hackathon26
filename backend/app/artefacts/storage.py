from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from pathlib import Path

import anyio

from app.config import get_settings


class StorageBackend(ABC):
    """Seam for Supabase Storage later; only the backend ever touches raw files."""

    @abstractmethod
    async def put(self, path: str, data: bytes) -> None: ...

    @abstractmethod
    async def get(self, path: str) -> bytes: ...

    @abstractmethod
    async def delete(self, path: str) -> None: ...


class LocalStorage(StorageBackend):
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _resolve(self, path: str) -> Path:
        full = (self.root / path).resolve()
        if self.root not in full.parents:
            raise ValueError("Path escapes storage root")
        return full

    async def put(self, path: str, data: bytes) -> None:
        full = self._resolve(path)
        await anyio.to_thread.run_sync(full.parent.mkdir, 0o755, True, True)
        await anyio.Path(full).write_bytes(data)

    async def get(self, path: str) -> bytes:
        return await anyio.Path(self._resolve(path)).read_bytes()

    async def delete(self, path: str) -> None:
        p = anyio.Path(self._resolve(path))
        if await p.exists():
            await p.unlink()


_storage: StorageBackend | None = None


def get_storage() -> StorageBackend:
    global _storage
    if _storage is None:
        _storage = LocalStorage(get_settings().storage_dir)
    return _storage


def set_storage(storage: StorageBackend | None) -> None:
    global _storage
    _storage = storage


def object_path(course_id: uuid.UUID, artefact_id: uuid.UUID, ext: str) -> str:
    """Server-generated path only — never derived from the client filename."""
    return f"courses/{course_id}/{artefact_id}.{ext}"
