from __future__ import annotations

import sqlite3

import pytest

from video_playlist_downloader.persistence import (
    PersistenceConfig,
    ResumeCheckpoint,
    configure_persistence,
    save_resume_checkpoint,
)


@pytest.mark.usefixtures("storage_root")
def test_save_resume_checkpoint_retries_on_operational_error(monkeypatch, app_config):
    attempts = {"execute": 0}

    configure_persistence(PersistenceConfig(database_path=app_config.storage.database))

    class FlakyConnection:
        def __init__(self) -> None:
            self.closed = False

        def execute(self, *args, **kwargs):
            attempts["execute"] += 1
            if attempts["execute"] == 1:
                raise sqlite3.OperationalError("database is locked")
            return self

        def executemany(self, *args, **kwargs):
            return self

        def commit(self):
            attempts.setdefault("commit", 0)
            attempts["commit"] += 1

        def close(self):
            self.closed = True

    def flaky_connect(*args, **kwargs):
        return FlakyConnection()

    monkeypatch.setattr("video_playlist_downloader.persistence.sqlite3.connect", flaky_connect)

    checkpoint = ResumeCheckpoint(
        session_id="session-retry",
        playlist_id="playlist-xyz",
        playlist_url="https://example.com/playlist",
        completed_videos=("video-1",),
        pending_videos=("video-2",),
        throttle_profile={
            "maxConcurrency": 1,
            "limitRate": None,
            "sleepIntervalSeconds": 1.0,
        },
        resumed_from=None,
    )

    save_resume_checkpoint(app_config.storage.database, checkpoint)

    assert attempts["execute"] >= 2
    assert attempts["commit"] >= 1
