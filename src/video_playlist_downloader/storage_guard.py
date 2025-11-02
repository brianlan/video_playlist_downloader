"""
Storage capacity safeguards for download operations.
"""

from __future__ import annotations

from dataclasses import dataclass
import shutil
from pathlib import Path


class InsufficientStorageError(RuntimeError):
    """Raised when remaining disk capacity drops below the configured threshold."""

    def __init__(self, free_bytes: int, required_bytes: int, path: Path) -> None:
        self.free_bytes = free_bytes
        self.required_bytes = required_bytes
        self.path = path
        super().__init__(
            f"Insufficient storage at {path}: {free_bytes} bytes free, "
            f"{required_bytes} bytes required."
        )


def _to_bytes_from_gigabytes(gigabytes: float) -> int:
    return int(gigabytes * 1024 * 1024 * 1024)


@dataclass
class StorageGuard:
    """
    Monitor disk availability for a target directory.
    """

    minimum_free_bytes: int

    @classmethod
    def from_gigabytes(cls, gigabytes: float) -> "StorageGuard":
        return cls(minimum_free_bytes=_to_bytes_from_gigabytes(gigabytes))

    def ensure_capacity(self, path: Path) -> None:
        """Raise InsufficientStorageError if the directory lacks required space."""
        resolved_path = path if path.is_dir() else path.parent
        usage = shutil.disk_usage(resolved_path)
        if usage.free < self.minimum_free_bytes:
            raise InsufficientStorageError(
                free_bytes=usage.free,
                required_bytes=self.minimum_free_bytes,
                path=resolved_path,
            )


__all__ = ["StorageGuard", "InsufficientStorageError"]
