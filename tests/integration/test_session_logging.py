from __future__ import annotations

import sqlite3
import json
from uuid import NAMESPACE_URL, UUID, uuid5

import pytest

from video_playlist_downloader import cli
from video_playlist_downloader.downloader import DownloadSummary, SkipRecord
from video_playlist_downloader.persistence import load_playlist_manifest


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
        applied_concurrency=2,
        applied_limit_rate="2M",
        sleep_interval=1.0,
        manifest={
            "playlistUrl": playlist_url,
            "videos": [
                {"url": "https://example.com/video1"},
                {"url": "https://example.com/video2"},
                {"url": "https://example.com/video3"},
            ],
        },
        completed_videos=(
            "https://example.com/video1",
            "https://example.com/video2",
            "https://example.com/video3",
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
    session_line = next(line for line in result.stdout.splitlines() if line.startswith("Session ID:"))
    reported_session_id = session_line.split(":", 1)[1].strip()

    connection = sqlite3.connect(app_config.storage.database)
    connection.row_factory = sqlite3.Row
    try:
        activity_rows = connection.execute(
            "SELECT session_id, playlist_id, playlist_url, status, total, completed, skipped, failed, pending, "
            "throttle_label, throttle_max_concurrency, throttle_limit_rate FROM session_activity"
        ).fetchall()
        assert len(activity_rows) == 1
        (
            session_id,
            playlist_id,
            row_playlist_url,
            status,
            total,
            completed,
            skipped,
            failed,
            pending,
            throttle_label,
            throttle_max_concurrency,
            throttle_limit_rate,
        ) = activity_rows[0]
        UUID(session_id)
        assert session_id == reported_session_id
        assert row_playlist_url == playlist_url
        assert playlist_id == str(uuid5(NAMESPACE_URL, playlist_url))
        assert status == "completed"
        assert (total, completed, skipped, failed, pending) == (4, 3, 1, 0, 0)
        assert throttle_label == "2 concurrent @ 2M"
        assert throttle_max_concurrency == 2
        assert throttle_limit_rate == "2M"

        skip_rows = connection.execute(
            "SELECT session_id, video_url, reason FROM session_skips"
        ).fetchall()
        assert len(skip_rows) == 1
        skip_session_id, video_url, reason = skip_rows[0]
        assert skip_session_id == session_id
        assert video_url == "https://example.com/video1"
        assert reason == "geo-block"

        checkpoint_rows = connection.execute(
            "SELECT session_id, completed_videos, pending_videos, manifest, resumed_from, throttle_profile "
            "FROM resume_checkpoints"
        ).fetchall()
        assert len(checkpoint_rows) == 1
        checkpoint_row = checkpoint_rows[0]
        assert checkpoint_row["session_id"] == session_id
        assert checkpoint_row["resumed_from"] is None
        assert json.loads(checkpoint_row["completed_videos"]) == list(summary.completed_videos)
        assert json.loads(checkpoint_row["pending_videos"]) == list(summary.pending_videos)
        persisted_manifest = json.loads(checkpoint_row["manifest"])
        assert persisted_manifest["playlistUrl"] == playlist_url
        throttle_profile = json.loads(checkpoint_row["throttle_profile"])
        assert throttle_profile["maxConcurrency"] == summary.applied_concurrency
    finally:
        connection.close()

    quality_path = app_config.storage.reports / "quality-summary.md"
    assert quality_path.exists()
    contents = quality_path.read_text()
    assert "Quality Summary" in contents

    manifest = load_playlist_manifest(app_config.storage.database, str(uuid5(NAMESPACE_URL, playlist_url)))
    assert manifest is not None
