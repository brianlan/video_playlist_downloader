from __future__ import annotations

import sqlite3
from uuid import UUID

import pytest

from video_playlist_downloader import cli
from video_playlist_downloader.downloader import DownloadSummary, SkipRecord


@pytest.mark.usefixtures("storage_root")
def test_download_logs_session_activity_and_skips(monkeypatch, cli_runner, app_config):
    playlist_url = "https://example.com/playlist"
    summary = DownloadSummary(
        total=4,
        completed=3,
        skipped=1,
        failed=0,
        pending=0,
        throttle_label="2 concurrent @ 2M",
        elapsed_seconds=10.0,
        eta_seconds=0.0,
        skipped_items=(
            SkipRecord(video_url="https://example.com/video1", reason="geo-block"),
        ),
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

    connection = sqlite3.connect(app_config.storage.database)
    try:
        activity_rows = connection.execute(
            "SELECT session_id, playlist_url, total, completed, skipped, failed, pending, throttle_label "
            "FROM session_activity"
        ).fetchall()
        assert len(activity_rows) == 1
        session_id, row_playlist_url, total, completed, skipped, failed, pending, throttle_label = activity_rows[0]
        UUID(session_id)
        assert row_playlist_url == playlist_url
        assert (total, completed, skipped, failed, pending) == (4, 3, 1, 0, 0)
        assert throttle_label == "2 concurrent @ 2M"

        skip_rows = connection.execute(
            "SELECT session_id, video_url, reason FROM session_skips"
        ).fetchall()
        assert len(skip_rows) == 1
        skip_session_id, video_url, reason = skip_rows[0]
        assert skip_session_id == session_id
        assert video_url == "https://example.com/video1"
        assert reason == "geo-block"
    finally:
        connection.close()
