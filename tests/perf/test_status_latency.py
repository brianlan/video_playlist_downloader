from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from video_playlist_downloader import cli


@pytest.mark.usefixtures("storage_root")
def test_status_command_renders_large_summary_quickly(monkeypatch, cli_runner, app_config):
    playlist_url = "https://example.com/playlist"
    row = {
        "session_id": "demo",
        "playlist_id": "demo-playlist",
        "status": "completed",
        "total": 500,
        "completed": 490,
        "skipped": 3,
        "failed": 5,
        "pending": 2,
        "throttle_label": "2 concurrent @ 2M",
        "throttle_max_concurrency": 2,
        "throttle_limit_rate": "2M",
        "throttle_sleep_interval": 1.0,
        "elapsed_seconds": 240.0,
        "eta_seconds": 60.0,
    }

    monkeypatch.setattr(cli, "_load_configuration", lambda _: app_config)
    monkeypatch.setattr(cli, "fetch_playlist_sessions", lambda db, url: [row])

    start = time.perf_counter()
    result = cli_runner.invoke(cli.app, ["status", "--playlist-url", playlist_url])
    duration = time.perf_counter() - start

    assert result.exit_code == 0
    assert duration < 2.0
    assert "Total Videos: 500" in result.stdout
    assert "Completed: 490" in result.stdout
    assert "Pending: 2" in result.stdout
    assert "Throttle: 2 concurrent @ 2M" in result.stdout
