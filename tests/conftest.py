"""
Shared pytest fixtures for the Video Playlist Downloader tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import pytest

from typer.testing import CliRunner

from video_playlist_downloader.config import AppConfig, StoragePaths, ThrottleSettings

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


@pytest.fixture
def app_config(storage_root: Path) -> AppConfig:
    """Provide a concrete application configuration rooted in a temp directory."""
    downloads = storage_root / "downloads"
    database = storage_root / "state.db"
    reports = storage_root / "reports"
    return AppConfig(
        storage=StoragePaths(
            root=storage_root,
            downloads=downloads,
            database=database,
            reports=reports,
        ),
        throttle=ThrottleSettings(),
        subtitle_languages=(),
        env_file=None,
    )


@pytest.fixture
def cli_runner() -> CliRunner:
    """Typer CLI runner for invoking commands in tests."""
    return CliRunner()
