from __future__ import annotations

import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from video_playlist_downloader import metadata


@pytest.mark.performance
def test_metadata_batch_persistence_under_five_seconds():
    engine = create_engine("sqlite:///:memory:", future=True)
    metadata.create_metadata_schema(engine)
    Session = sessionmaker(engine, future=True)
    session = Session()

    repo = metadata.MetadataRepository(session)
    playlist = repo.create_playlist(
        source_url="https://example.com/perf",
        title="Perf Playlist",
        item_count=500,
    )

    batch = [
        metadata.VideoMetadataInput(
            playlist=playlist,
            video_url=f"https://example.com/perf/{idx}",
            title=f"Video {idx}",
            duration_seconds=60,
            publish_time=None,
            bvid=f"BV{idx}",
            description=None,
        )
        for idx in range(500)
    ]

    start = time.perf_counter()
    repo.persist_video_batch(batch)
    elapsed = time.perf_counter() - start

    assert elapsed <= 5.0
