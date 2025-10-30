"""
Playlist download orchestration logic.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Iterable, List, Optional, Sequence

from .config import AppConfig, ThrottleSettings


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

    def _format_throttle_label(
        self,
        throttle: ThrottleSettings,
        *,
        max_concurrency: Optional[int],
        limit_rate: Optional[str],
    ) -> str:
        concurrency = max_concurrency or throttle.max_concurrency
        rate = limit_rate or throttle.limit_rate or "unbounded"
        return f"{concurrency} concurrent @ {rate}"

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

        throttle_label = self._format_throttle_label(
            self.config.throttle,
            max_concurrency=max_concurrency,
            limit_rate=limit_rate,
        )

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
        )


__all__ = ["DownloadSummary", "PlaylistDownloader"]
