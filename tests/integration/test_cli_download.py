from __future__ import annotations

from types import SimpleNamespace

import pytest

from video_playlist_downloader import cli
from video_playlist_downloader.config import AppConfig


@pytest.mark.usefixtures("storage_root")
def test_download_command_initializes_persistence(monkeypatch, cli_runner, app_config: AppConfig):
    playlist_url = "https://example.com/playlist"
    summary = SimpleNamespace(
        total=3,
        completed=3,
        skipped=0,
        failed=0,
        pending=0,
        throttle_label="default",
        elapsed_seconds=5.0,
        eta_seconds=0.0,
    )

    monkeypatch.setattr(cli, "_load_configuration", lambda _: app_config)

    configure_calls: list[object] = []

    def fake_configure_persistence(config) -> None:
        configure_calls.append(config)
        config.database_path.parent.mkdir(parents=True, exist_ok=True)
        config.database_path.touch(exist_ok=True)

    monkeypatch.setattr(cli, "configure_persistence", fake_configure_persistence)

    class StubDownloader:
        def __init__(self, *, config, playlist_url: str) -> None:
            self.config = config
            self.playlist_url = playlist_url

        def run(self, *, max_concurrency=None, limit_rate=None):
            return summary

    monkeypatch.setattr(cli, "PlaylistDownloader", StubDownloader)

    result = cli_runner.invoke(cli.app, ["download", playlist_url])

    assert result.exit_code == 0
    assert configure_calls, "configure_persistence should be invoked"
    assert configure_calls[0].database_path == app_config.storage.database
    assert app_config.storage.database.exists(), "State database should be created"
    assert app_config.storage.reports.exists(), "Reports directory should be created"
    assert "Download Summary" in result.stdout
