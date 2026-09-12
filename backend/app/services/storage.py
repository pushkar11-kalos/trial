"""
Local filesystem storage backend, deliberately shaped so a future S3Backend
can drop in behind the same three-method interface without touching callers.
"""
import os
import re
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

from ..config import settings


def safe_filename(original_name: str) -> str:
    """Strip any path components and non-safe characters, keep the extension."""
    base = os.path.basename(original_name or "upload")
    base = re.sub(r"[^A-Za-z0-9_.-]", "_", base)
    ext = Path(base).suffix.lower()
    if len(ext) > 10:  # guard against a malicious "extension"
        ext = ""
    return f"{uuid.uuid4().hex}{ext}"


class StorageBackend(ABC):
    @abstractmethod
    def save(self, relative_dir: str, original_filename: str, data: bytes) -> str:
        """Persist bytes, return the relative path (used as Evidence.file_path)."""

    @abstractmethod
    def read(self, relative_path: str) -> bytes:
        ...

    @abstractmethod
    def absolute_path(self, relative_path: str) -> str:
        ...

    @abstractmethod
    def delete(self, relative_path: str) -> None:
        ...


class LocalStorageBackend(StorageBackend):
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.STORAGE_ROOT).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, relative_dir: str, original_filename: str, data: bytes) -> str:
        target_dir = (self.root / relative_dir).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = safe_filename(original_filename)
        full_path = target_dir / filename
        with open(full_path, "wb") as f:
            f.write(data)
        return str(Path(relative_dir) / filename)

    def read(self, relative_path: str) -> bytes:
        with open(self.absolute_path(relative_path), "rb") as f:
            return f.read()

    def absolute_path(self, relative_path: str) -> str:
        return str((self.root / relative_path).resolve())

    def delete(self, relative_path: str) -> None:
        try:
            os.remove(self.absolute_path(relative_path))
        except FileNotFoundError:
            pass


_backend: StorageBackend | None = None


def get_storage() -> StorageBackend:
    global _backend
    if _backend is None:
        # STORAGE_BACKEND is read here (not module import time) so tests can
        # override settings.STORAGE_ROOT before first use.
        _backend = LocalStorageBackend(settings.STORAGE_ROOT)
    return _backend
