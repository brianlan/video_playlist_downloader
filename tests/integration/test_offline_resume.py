from __future__ import annotations

import json

import pytest

from video_playlist_downloader import cli
from video_playlist_downloader.downloader import DownloadSummary
from video_playlist_downloader.persistence import (
    PersistenceConfig,
    ResumeCheckpoint,
    configure_persistence,
    save_resume_checkpoint,
)


@pytest.mark.usefixtures("storage_root")
def test_resume_uses_checkpoint_without_network(monkeypatch, cli_runner, app_config):
    playlist_url = "https://example.com/playlist"
    database_path = app_config.storage.database

    configure_persistence(PersistenceConfig(database_path=database_path))

    checkpoint = ResumeCheckpoint(
        session_id="session-123",
        playlist_id="playlist-abc",
        playlist_url=playlist_url,
        completed_videos=("video-a",),
        pending_videos=("video-b", "video-c"),
        throttle_profile={
            "maxConcurrency": 2,
            "limitRate": "2M",
            "sleepIntervalSeconds": 1.0,
        },
        resumed_from=None,
    )

    save_resume_checkpoint(database_path, checkpoint)

    summary = DownloadSummary(
        total=3,
        completed=2,
        skipped=1,
        failed=0,
        pending=0,
        throttle_label="2 concurrent @ 2M",
        elapsed_seconds=5.5,
        eta_seconds=0.0,
        applied_concurrency=2,
        applied_limit_rate="2M",
        sleep_interval=1.0,
    )

    monkeypatch.setattr(cli, "_load_configuration", lambda _: app_config)

    class StubDownloader:
        def __init__(self, *, config, playlist_url: str) -> None:
            self.config = config
            self.playlist_url = playlist_url

        def run(self, *args, **kwargs):  # pragma: no cover - should not be called
            raise AssertionError("run should not be invoked during resume")

        def resume_from_checkpoint(self, checkpoint_payload):
            assert checkpoint_payload.session_id == checkpoint.session_id
            return summary

    monkeypatch.setattr(cli, "PlaylistDownloader", StubDownloader)

    result = cli_runner.invoke(
        cli.app,
        ["resume", checkpoint.session_id, "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout.strip())
    assert payload["videosCompleted"] == summary.completed
    assert payload["videosSkipped"] == summary.skipped
