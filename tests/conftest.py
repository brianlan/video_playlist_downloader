"""
Shared pytest fixtures for the Video Playlist Downloader tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import pytest


@pytest.fixture
def storage_root(tmp_path: Path) -> Path:
    """Provide an isolated storage directory for tests."""
    root = tmp_path / "video-storage"
    root.mkdir()
    return root


class FakeYtDlpClient:
    """Minimal stub that records playlist downloads."""

    def __init__(self) -> None:
        self.download_calls: List[Iterable[str]] = []

    def download(self, urls: Iterable[str]) -> None:
        self.download_calls.append(tuple(urls))


@pytest.fixture
def fake_yt_dlp() -> FakeYtDlpClient:
    """Return a fake yt-dlp client used in tests."""
    return FakeYtDlpClient()
