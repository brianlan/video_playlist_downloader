from __future__ import annotations

import pytest

from video_playlist_downloader import cli
from video_playlist_downloader.storage_guard import InsufficientStorageError


@pytest.mark.usefixtures("storage_root")
def test_download_aborts_when_storage_is_low(monkeypatch, cli_runner, app_config):
    playlist_url = "https://example.com/playlist"

    monkeypatch.setattr(cli, "_load_configuration", lambda _: app_config)

    class GuardStub:
        def __init__(self, minimum_free_bytes: int) -> None:
            self.minimum_free_bytes = minimum_free_bytes

        @classmethod
        def from_gigabytes(cls, gigabytes: float) -> "GuardStub":
            return cls(int(gigabytes * (1024**3)))

        def ensure_capacity(self, path):
            raise InsufficientStorageError(
                free_bytes=128,
                required_bytes=self.minimum_free_bytes,
                path=path,
            )

    monkeypatch.setattr(cli, "StorageGuard", GuardStub)

    downloader_called = {"called": False}

    class StubDownloader:
        def __init__(self, *, config, playlist_url: str) -> None:
            downloader_called["called"] = True

        def run(self, *, max_concurrency=None, limit_rate=None):
            raise AssertionError("Downloader should not run when storage is insufficient")

    monkeypatch.setattr(cli, "PlaylistDownloader", StubDownloader)

    result = cli_runner.invoke(cli.app, ["download", playlist_url])

    combined_output = result.stdout + (result.stderr or "")

    assert result.exit_code != 0
    assert "Insufficient storage" in combined_output
    assert not downloader_called["called"], "Downloader should not run when capacity guard fails"
