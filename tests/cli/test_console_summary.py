from __future__ import annotations

from types import SimpleNamespace

import pytest

from video_playlist_downloader import cli


@pytest.mark.usefixtures("storage_root")
def test_console_summary_contains_key_metrics(monkeypatch, cli_runner, app_config):
    playlist_url = "https://example.com/playlist"
    summary = SimpleNamespace(
        total=10,
        completed=6,
        skipped=2,
        failed=1,
        pending=1,
        throttle_label="2 concurrent / 2M",
        elapsed_seconds=120.5,
        eta_seconds=30.0,
    )

    monkeypatch.setattr(cli, "_load_configuration", lambda _: app_config)

    class StubDownloader:
        def __init__(self, *, config, playlist_url: str) -> None:
            self.config = config
            self.playlist_url = playlist_url

        def run(self, *, max_concurrency=None, limit_rate=None):
            return summary

    monkeypatch.setattr(cli, "PlaylistDownloader", StubDownloader)

    result = cli_runner.invoke(cli.app, ["download", playlist_url])

    assert result.exit_code == 0
    assert "Download Summary" in result.stdout
    assert "Totals: 10" in result.stdout
    assert "Completed: 6" in result.stdout
    assert "Skipped: 2" in result.stdout
    assert "Pending: 1" in result.stdout
    assert "Throttle: 2 concurrent / 2M" in result.stdout
    assert "Elapsed: 120.5s" in result.stdout
    assert "ETA: 30.0s" in result.stdout
