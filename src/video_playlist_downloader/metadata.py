"""
Metadata models and repository helpers for the Video Playlist Downloader.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

try:  # pragma: no cover - import guard for environments without SQLAlchemy
    from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, select
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session

    SQLALCHEMY_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - fallback definitions
    DateTime = ForeignKey = Integer = String = Text = None  # type: ignore
    DeclarativeBase = object  # type: ignore
    Mapped = mapped_column = relationship = Session = None  # type: ignore
    SQLALCHEMY_AVAILABLE = False
    _IMPORT_ERROR = ModuleNotFoundError("SQLAlchemy is required for metadata persistence")


if SQLALCHEMY_AVAILABLE:

    class Base(DeclarativeBase):
        """Declarative base for metadata models."""


    class Playlist(Base):
        """Represents a downloaded playlist."""

        __tablename__ = "playlists"

        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        source_url: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
        title: Mapped[str] = mapped_column(String(255), nullable=False)
        item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
        last_crawled_at: Mapped[Optional[Any]] = mapped_column(DateTime(timezone=True))
        cursor: Mapped[Optional[str]] = mapped_column(String(255))

        videos: Mapped[list[VideoRecord]] = relationship(
            "VideoRecord",
            back_populates="playlist",
            cascade="all, delete-orphan",
        )


    class VideoRecord(Base):
        """Represents a persisted video within a playlist."""

        __tablename__ = "video_records"

        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        playlist_id: Mapped[int] = mapped_column(ForeignKey("playlists.id"), nullable=False, index=True)
        video_url: Mapped[str] = mapped_column(String(512), nullable=False)
        bvid: Mapped[Optional[str]] = mapped_column(String(64))
        title: Mapped[str] = mapped_column(String(255), nullable=False)
        description: Mapped[Optional[str]] = mapped_column(Text)
        publish_time: Mapped[Optional[Any]] = mapped_column(DateTime(timezone=True))
        duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
        local_path: Mapped[Optional[str]] = mapped_column(String(512))
        download_status: Mapped[str] = mapped_column(String(32), default="pending")
        skip_reason: Mapped[Optional[str]] = mapped_column(String(255))
        last_attempted_at: Mapped[Optional[Any]] = mapped_column(DateTime(timezone=True))

        playlist: Mapped[Playlist] = relationship("Playlist", back_populates="videos")
        subtitles: Mapped[Optional[SubtitleAsset]] = relationship(
            "SubtitleAsset",
            back_populates="video",
            cascade="all, delete-orphan",
            uselist=False,
        )


    class SubtitleAsset(Base):
        """Represents a subtitle track associated with a video."""

        __tablename__ = "subtitle_assets"

        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        video_id: Mapped[int] = mapped_column(ForeignKey("video_records.id"), nullable=False, unique=True)
        language_code: Mapped[str] = mapped_column(String(16), nullable=False)
        format: Mapped[str] = mapped_column(String(16), nullable=False)
        local_path: Mapped[str] = mapped_column(String(512), nullable=False)
        source_url: Mapped[Optional[str]] = mapped_column(String(512))

        video: Mapped[VideoRecord] = relationship("VideoRecord", back_populates="subtitles")


    def create_metadata_schema(engine: Any) -> None:
        """Create metadata tables on the provided engine."""

        Base.metadata.create_all(bind=engine)


else:  # pragma: no cover - used only when SQLAlchemy unavailable

    class Base:  # type: ignore[misc]
        metadata = None

    class Playlist:  # type: ignore[misc]
        pass

    class VideoRecord:  # type: ignore[misc]
        pass

    class SubtitleAsset:  # type: ignore[misc]
        pass

    def create_metadata_schema(engine: Any) -> None:  # type: ignore[unused-argument]
        raise _IMPORT_ERROR


@dataclass
class VideoMetadataInput:
    """Input payload describing a video to persist."""

    playlist: Playlist
    video_url: str
    title: str
    duration_seconds: Optional[int]
    publish_time: Optional[Any]
    bvid: Optional[str]
    description: Optional[str]
    download_status: str = "completed"
    subtitles: Optional[Dict[str, Any]] = None


if SQLALCHEMY_AVAILABLE:

    class MetadataRepository:
        """High level facade for metadata persistence operations."""

        def __init__(self, session: Session) -> None:
            self._session = session

        def get_playlist_by_source_url(self, source_url: str) -> Optional[Playlist]:
            stmt = select(Playlist).where(Playlist.source_url == source_url)
            return self._session.execute(stmt).scalar_one_or_none()

        def create_playlist(
            self,
            *,
            source_url: str,
            title: str,
            item_count: int,
        ) -> Playlist:
            playlist = Playlist(
                source_url=source_url,
                title=title,
                item_count=item_count,
            )
            self._session.add(playlist)
            self._session.flush()
            return playlist

        def add_video(
            self,
            *,
            playlist: Playlist,
            video_url: str,
            title: str,
            duration_seconds: Optional[int],
            publish_time: Optional[Any],
            bvid: Optional[str],
            description: Optional[str],
        ) -> VideoRecord:
            stmt = select(VideoRecord).where(
                VideoRecord.playlist_id == playlist.id,
                VideoRecord.video_url == video_url,
            )
            record = self._session.execute(stmt).scalar_one_or_none()
            if record is None:
                record = VideoRecord(
                    playlist=playlist,
                    video_url=video_url,
                )
                self._session.add(record)

            record.title = title
            record.duration_seconds = duration_seconds
            record.publish_time = publish_time
            record.bvid = bvid
            record.description = description
            record.download_status = "completed"
            self._session.flush()
            return record

        def persist_video_batch(self, videos: Sequence[VideoMetadataInput]) -> None:
            """Persist a batch of videos efficiently."""

            for video in videos:
                record = self.add_video(
                    playlist=video.playlist,
                    video_url=video.video_url,
                    title=video.title,
                    duration_seconds=video.duration_seconds,
                    publish_time=video.publish_time,
                    bvid=video.bvid,
                    description=video.description,
                )
                if video.subtitles:
                    self._apply_subtitle(record, video.subtitles)
            self._session.flush()

        def _apply_subtitle(self, record: VideoRecord, subtitle_data: Dict[str, Any]) -> None:
            local_path = subtitle_data.get("local_path") or subtitle_data.get("path") or ""
            language = subtitle_data.get("language") or subtitle_data.get("language_code") or "und"
            format_ = subtitle_data.get("format") or subtitle_data.get("extension") or "vtt"
            source_url = subtitle_data.get("url")

            if record.subtitles is None:
                record.subtitles = SubtitleAsset(
                    language_code=language,
                    format=format_,
                    local_path=local_path,
                    source_url=source_url,
                )
            else:
                record.subtitles.language_code = language
                record.subtitles.format = format_
                record.subtitles.local_path = local_path
                record.subtitles.source_url = source_url

        def subtitle_coverage(self, playlist: Playlist) -> Dict[str, Any]:
            total_stmt = select(func.count(VideoRecord.id)).where(VideoRecord.playlist_id == playlist.id)
            total = self._session.execute(total_stmt).scalar_one()

            subtitle_stmt = (
                select(func.count(SubtitleAsset.id))
                .join(VideoRecord, SubtitleAsset.video_id == VideoRecord.id)
                .where(VideoRecord.playlist_id == playlist.id)
            )
            with_subtitles = self._session.execute(subtitle_stmt).scalar_one()

            language_rows = self._session.execute(
                select(SubtitleAsset.language_code, func.count(SubtitleAsset.id))
                .join(VideoRecord, SubtitleAsset.video_id == VideoRecord.id)
                .where(VideoRecord.playlist_id == playlist.id)
                .group_by(SubtitleAsset.language_code)
            ).all()
            languages = {row[0]: row[1] for row in language_rows}

            return generate_subtitle_coverage_report(
                total_videos=total,
                videos_with_subtitles=with_subtitles,
                languages=languages,
            )

        def persist_manifest(self, playlist: Playlist, videos: Sequence[Any]) -> None:
            for entry in videos:
                if isinstance(entry, dict):
                    video_url = entry.get("url") or entry.get("video_url") or entry.get("id")
                    title = entry.get("title") or video_url
                    duration = entry.get("duration")
                    publish_time = entry.get("publish_time")
                    bvid = entry.get("bvid")
                    description = entry.get("description")
                    subtitles = entry.get("subtitles") or []
                else:
                    video_url = str(entry)
                    title = video_url
                    duration = None
                    publish_time = None
                    bvid = None
                    description = None
                    subtitles = []

                record = self.add_video(
                    playlist=playlist,
                    video_url=video_url,
                    title=title,
                    duration_seconds=duration,
                    publish_time=publish_time,
                    bvid=bvid,
                    description=description,
                )

                if subtitles:
                    self._apply_subtitle(record, subtitles[0])

            self._session.flush()



else:  # pragma: no cover - used in environments lacking SQLAlchemy

    class MetadataRepository:  # type: ignore[misc]
        def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
            raise _IMPORT_ERROR


def generate_subtitle_coverage_report(
    *,
    total_videos: int,
    videos_with_subtitles: int,
    languages: Dict[str, int],
) -> Dict[str, Any]:
    coverage_percent = 0
    if total_videos > 0:
        coverage_percent = int((videos_with_subtitles / total_videos) * 100)
    return {
        "totalVideos": total_videos,
        "videosWithSubtitles": videos_with_subtitles,
        "coveragePercent": coverage_percent,
        "languages": languages,
    }


__all__ = [
    "Base",
    "Playlist",
    "VideoRecord",
    "SubtitleAsset",
    "create_metadata_schema",
    "MetadataRepository",
    "VideoMetadataInput",
    "generate_subtitle_coverage_report",
]
