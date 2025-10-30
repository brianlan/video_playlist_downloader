from __future__ import annotations

from pathlib import Path

import pytest

from video_playlist_downloader.persistence import (
    PersistenceConfig,
    ResumeCheckpoint,
    configure_persistence,
    load_resume_checkpoint,
    save_resume_checkpoint,
)


@pytest.mark.usefixtures("storage_root")
def test_resume_checkpoint_round_trip(app_config, storage_root: Path) -> None:
    database_path = app_config.storage.database
    configure_persistence(PersistenceConfig(database_path=database_path))

    checkpoint = ResumeCheckpoint(
        session_id="session-123",
        playlist_id="playlist-abc",
        playlist_url="https://example.com/playlist",
        completed_videos=("video-a", "video-b"),
        pending_videos=("video-c",),
        throttle_profile={
            "maxConcurrency": 2,
            "limitRate": "2M",
            "sleepIntervalSeconds": 1.0,
        },
        resumed_from=None,
    )

    save_resume_checkpoint(database_path, checkpoint)

    loaded = load_resume_checkpoint(database_path, "session-123")
    assert loaded == checkpoint
