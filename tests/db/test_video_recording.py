from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker

from video_playlist_downloader import metadata


@pytest.fixture
def memory_engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    metadata.create_metadata_schema(engine)
    return engine


def test_video_record_persists_playlist_relationship(memory_engine):
    Session = sessionmaker(memory_engine, future=True)
    session = Session()

    repo = metadata.MetadataRepository(session)
    playlist = repo.create_playlist(
        source_url="https://example.com/playlist",
        title="Example Playlist",
        item_count=3,
    )

    repo.add_video(
        playlist=playlist,
        video_url="https://example.com/video/1",
        title="Demo Video",
        duration_seconds=120,
        publish_time=None,
        bvid="BV123",
        description="Sample",
    )
    session.commit()

    stored_playlist = session.query(metadata.Playlist).filter_by(source_url=playlist.source_url).one()
    assert stored_playlist.item_count == 3
    assert len(stored_playlist.videos) == 1


def test_metadata_tables_exist(memory_engine):
    insp = memory_engine.dialect.get_table_names(memory_engine.connect())
    expected_tables = {"playlists", "video_records", "subtitle_assets"}
    for table_name in expected_tables:
        assert table_name in insp, f"Expected table {table_name} to be created"
