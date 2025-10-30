"""
Playlist download orchestration logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .config import AppConfig

if TYPE_CHECKING:  # pragma: no cover - only for type checking
    from .persistence import ResumeCheckpoint


@dataclass(frozen=True)
class SkipRecord:
    """Details about a skipped video."""

    video_url: str
    reason: str


@dataclass(frozen=True)
class DownloadSummary:
    """Aggregate information about a playlist download run."""

    total: int
    completed: int
    skipped: int
    failed: int
    pending: int
    throttle_label: str
    elapsed_seconds: float
    eta_seconds: float
    applied_concurrency: int
    applied_limit_rate: Optional[str]
    sleep_interval: float
    skipped_items: Tuple[SkipRecord, ...] = field(default_factory=tuple)
    manifest: Optional[Dict[str, Any]] = None


class PlaylistDownloader:
    """
    Coordinate playlist enumeration, throttled downloads, and result aggregation.

    The concrete download mechanics will be expanded in subsequent tasks. For now the
    downloader prepares the structures needed by the CLI and tests while exposing clear
    extension points for yt-dlp integration.
    """

    def __init__(
        self,
        *,
        config: AppConfig,
        playlist_url: str,
        yt_dlp_client: Optional[object] = None,
    ) -> None:
        self.config = config
        self.playlist_url = playlist_url
        self._yt_dlp_client = yt_dlp_client

    def enumerate_videos(self) -> Sequence[str]:
        """
        Return an ordered collection of video identifiers to download.

        The default implementation is a placeholder that yields an empty sequence.
        """

        return []

    def _download_videos(self, video_ids: Iterable[str]) -> List[str]:
        """
        Execute downloads for the provided video identifiers.

        The placeholder implementation simply records the IDs that would have been
        downloaded and returns the successful ones.
        """

        return list(video_ids)

    def run(
        self,
        *,
        max_concurrency: Optional[int] = None,
        limit_rate: Optional[str] = None,
    ) -> DownloadSummary:
        """
        Execute the download process and return a summary of results.
        """

        start = time.perf_counter()
        videos = list(self.enumerate_videos())
        completed_videos = self._download_videos(videos)
        elapsed = time.perf_counter() - start

        applied_concurrency = max_concurrency or self.config.throttle.max_concurrency
        applied_limit_rate = limit_rate or self.config.throttle.limit_rate
        throttle_label = f"{applied_concurrency} concurrent @ {applied_limit_rate or 'unbounded'}"

        skipped = 0
        failed = len(videos) - len(completed_videos)
        pending = 0

        return DownloadSummary(
            total=len(videos),
            completed=len(completed_videos),
            skipped=skipped,
            failed=failed,
            pending=pending,
            throttle_label=throttle_label,
            elapsed_seconds=elapsed,
            eta_seconds=0.0,
            applied_concurrency=applied_concurrency,
            applied_limit_rate=applied_limit_rate,
            sleep_interval=self.config.throttle.sleep_interval,
            manifest={"playlistUrl": self.playlist_url, "videos": list(videos)},
        )


    def resume_from_checkpoint(
        self,
        checkpoint: "ResumeCheckpoint",
    ) -> DownloadSummary:
        """Resume downloads using data stored in a checkpoint."""

        applied_concurrency = (
            checkpoint.throttle_profile.get("maxConcurrency")
            or self.config.throttle.max_concurrency
        )
        applied_limit_rate = checkpoint.throttle_profile.get("limitRate")
        sleep_interval = checkpoint.throttle_profile.get(
            "sleepIntervalSeconds", self.config.throttle.sleep_interval
        )
        throttle_label = f"{applied_concurrency} concurrent @ {applied_limit_rate or 'unbounded'}"

        completed = list(checkpoint.completed_videos)
        pending_videos = list(checkpoint.pending_videos)
        if not pending_videos and checkpoint.manifest:
            manifest_videos = checkpoint.manifest.get("videos", [])
            completed_set = set(completed)
            pending_videos = [vid for vid in manifest_videos if vid not in completed_set]

        start = time.perf_counter()
        newly_completed = self._download_videos(pending_videos)
        elapsed = time.perf_counter() - start

        completed.extend(newly_completed)
        failed = len(pending_videos) - len(newly_completed)
        total_videos = (
            len(checkpoint.manifest.get("videos", []))
            if checkpoint.manifest
            else len(checkpoint.completed_videos) + len(checkpoint.pending_videos)
        )

        return DownloadSummary(
            total=total_videos,
            completed=len(completed),
            skipped=0,
            failed=failed,
            pending=0,
            throttle_label=throttle_label,
            elapsed_seconds=elapsed,
            eta_seconds=0.0,
            applied_concurrency=applied_concurrency,
            applied_limit_rate=applied_limit_rate,
            sleep_interval=sleep_interval,
            manifest=checkpoint.manifest,
        )


__all__ = ["DownloadSummary", "PlaylistDownloader", "SkipRecord"]
