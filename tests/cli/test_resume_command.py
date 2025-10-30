from __future__ import annotations

import json

import pytest

from video_playlist_downloader import cli
from video_playlist_downloader.downloader import DownloadSummary
from video_playlist_downloader.persistence import ResumeCheckpoint


@pytest.mark.usefixtures("storage_root")
def test_resume_cli_rehydrates_checkpoint(monkeypatch, cli_runner, app_config):
    playlist_url = "https://example.com/playlist"
    playlist_id = "playlist-abc"
    resume_session_id = "session-123"

    summary = DownloadSummary(
        total=4,
        completed=4,
        skipped=0,
        failed=0,
        pending=0,
        throttle_label="2 concurrent @ unbounded",
        elapsed_seconds=9.5,
        eta_seconds=0.0,
        applied_concurrency=2,
        applied_limit_rate=None,
        sleep_interval=1.0,
    )

    checkpoint = ResumeCheckpoint(
        session_id=resume_session_id,
        playlist_id=playlist_id,
        playlist_url=playlist_url,
        completed_videos=("video-a", "video-b"),
        pending_videos=("video-c", "video-d"),
        throttle_profile={
            "maxConcurrency": 2,
            "limitRate": None,
            "sleepIntervalSeconds": 1.0,
        },
        resumed_from="session-001",
    )

    monkeypatch.setattr(cli, "_load_configuration", lambda _: app_config)
    load_calls = {}
    monkeypatch.setattr(
        cli,
        "load_resume_checkpoint",
        lambda db, session_id: load_calls.setdefault("session_id", session_id) or checkpoint,
    )

    invoked = {}

    class StubDownloader:
        def __init__(self, *, config, playlist_url: str) -> None:
            invoked["config"] = config
            invoked["playlist_url"] = playlist_url

        def resume_from_checkpoint(self, checkpoint_payload):
            invoked["checkpoint"] = checkpoint_payload
            return summary

    monkeypatch.setattr(cli, "PlaylistDownloader", StubDownloader)

    result = cli_runner.invoke(
        cli.app,
        ["resume", resume_session_id, "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout.strip())
    assert payload["resumedFrom"] == resume_session_id
    assert payload["videosTotal"] == summary.total
    assert payload["videosCompleted"] == summary.completed
    assert payload["videosFailed"] == summary.failed
    assert {
        "session_id",
        "playlist_url",
    }.issubset(invoked["checkpoint"].__dict__.keys())
    assert load_calls["session_id"] == resume_session_id
