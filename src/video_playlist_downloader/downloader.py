"""
Playlist download orchestration logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .config import AppConfig
from .throttle import ThrottleController, ThrottleMetrics, ThrottleProfile
from .subtitles import select_subtitle_tracks

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
    throttle_metrics: ThrottleMetrics = field(default_factory=ThrottleMetrics)
    completed_videos: Tuple[str, ...] = field(default_factory=tuple)
    pending_videos: Tuple[str, ...] = field(default_factory=tuple)


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
        self._manifest_cache: Optional[Dict[str, Any]] = None

    def enumerate_videos(self) -> Sequence[Dict[str, Any]]:
        """
        Return an ordered collection of video identifiers to download.

        The default implementation loads the playlist manifest via yt-dlp and caches the
        normalized result for subsequent download phases.
        """

        manifest = self._load_manifest()
        return manifest.get("videos", [])

    def _get_client(self) -> object:
        if self._yt_dlp_client is not None:
            return self._yt_dlp_client
        try:
            from yt_dlp import YoutubeDL  # type: ignore
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError("yt-dlp is required to enumerate playlists.") from exc

        options = {
            "quiet": True,
            "ignoreerrors": True,
            "skip_download": True,
            "no_warnings": True,
        }
        self._yt_dlp_client = YoutubeDL(options)
        return self._yt_dlp_client

    def _load_manifest(self) -> Dict[str, Any]:
        if self._manifest_cache is not None:
            return self._manifest_cache

        client = self._get_client()
        info = client.extract_info(self.playlist_url, download=False)
        manifest = self._build_manifest(info)
        self._manifest_cache = manifest
        return manifest

    def _build_manifest(self, info: Dict[str, Any]) -> Dict[str, Any]:
        entries = info.get("entries") or []
        videos = []
        for raw_entry in entries:
            if not raw_entry:
                continue
            videos.append(self._normalize_entry(raw_entry))

        return {
            "id": info.get("id") or info.get("playlist_id"),
            "playlistUrl": self.playlist_url,
            "title": info.get("title") or self.playlist_url,
            "videos": videos,
        }

    def _normalize_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        url = entry.get("webpage_url") or entry.get("original_url") or entry.get("url")
        if not url and entry.get("id"):
            url = str(entry["id"])

        subtitles = self._normalize_subtitles(entry.get("subtitles"))

        publish_time = self._normalize_publish_time(
            entry.get("publish_time")
            or entry.get("timestamp")
            or entry.get("release_timestamp")
            or entry.get("upload_date")
        )

        return {
            "id": entry.get("id") or url,
            "url": url,
            "title": entry.get("title") or url,
            "duration": entry.get("duration"),
            "publish_time": publish_time,
            "bvid": entry.get("bvid"),
            "description": entry.get("description"),
            "availability": entry.get("availability") or entry.get("availability_status"),
            "skip_reason": entry.get("skip_reason"),
            "subtitles": subtitles,
        }

    def _normalize_subtitles(self, subtitles: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not subtitles:
            return []

        tracks: List[Dict[str, Any]] = []
        for language, entries in subtitles.items():
            if not entries:
                continue
            for track in entries:
                if not track:
                    continue
                url = track.get("url")
                if not url:
                    continue
                tracks.append(
                    {
                        "language": language,
                        "url": url,
                        "ext": track.get("ext"),
                        "name": track.get("name") or track.get("title"),
                    }
                )

        if not tracks:
            return []

        return select_subtitle_tracks(tracks, self.config.subtitle_languages or ())

    def _normalize_publish_time(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, datetime):
            dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        if isinstance(value, (int, float)):
            try:
                dt = datetime.fromtimestamp(value, tz=timezone.utc)
            except (OSError, OverflowError, ValueError):
                return None
            return dt.isoformat()
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return None
            if cleaned.isdigit() and len(cleaned) == 8:
                try:
                    dt = datetime.strptime(cleaned, "%Y%m%d")
                except ValueError:
                    return cleaned
                return dt.replace(tzinfo=timezone.utc).isoformat()
            try:
                dt = datetime.fromisoformat(cleaned)
            except ValueError:
                return cleaned
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        return str(value)

    def _entry_identifier(self, entry: Dict[str, Any]) -> str:
        url = self._entry_url(entry)
        if url is not None:
            return url
        identifier = entry.get("id")
        return str(identifier) if identifier is not None else ""

    def _entry_url(self, entry: Dict[str, Any]) -> Optional[str]:
        url = entry.get("url")
        if url:
            return str(url)
        return None

    def _download_videos(
        self,
        video_entries: Iterable[Dict[str, Any]],
        throttle: ThrottleController,
    ) -> Tuple[List[Dict[str, Any]], List[SkipRecord], List[Dict[str, Any]]]:
        """
        Execute downloads for the provided video identifiers while passing through
        the throttle controller to collect metrics.
        """

        completed: List[Dict[str, Any]] = []
        skipped: List[SkipRecord] = []
        failed: List[Dict[str, Any]] = []

        for entry in video_entries:
            skip_reason = self._should_skip_entry(entry)
            if skip_reason:
                skipped.append(
                    SkipRecord(
                        video_url=self._entry_identifier(entry),
                        reason=skip_reason,
                    )
                )
                continue

            with throttle.guard() as ticket:
                success = self._perform_download(entry)
                if success:
                    ticket.mark_success()
                    completed.append(entry)
                else:
                    ticket.mark_failure()
                    failed.append(entry)
        return completed, skipped, failed

    def _should_skip_entry(self, entry: Dict[str, Any]) -> Optional[str]:
        skip_reason = entry.get("skip_reason")
        if skip_reason:
            return str(skip_reason)

        availability = entry.get("availability")
        if availability:
            availability_str = str(availability).lower()
            if availability_str not in {"available", "public", "open"}:
                return f"Unavailable ({availability})"

        return None

    def _perform_download(self, entry: Dict[str, Any]) -> bool:
        """
        Perform the actual download. The placeholder implementation simply reports
        success and uses the yt-dlp client when provided.
        """

        video_url = self._entry_url(entry)
        if not video_url:
            return False

        client = self._get_client()
        try:
            client.download([video_url])
        except Exception:  # pragma: no cover - simulated failures handled by tests
            return False
        return True

    def _calculate_eta(self, remaining: int) -> float:
        if remaining <= 0:
            return True
        return remaining * max(0.0, self.config.throttle.sleep_interval)

    def run(
        self,
        *,
        max_concurrency: Optional[int] = None,
        limit_rate: Optional[str] = None,
    ) -> DownloadSummary:
        """
        Execute the download process and return a summary of results.
        """

        applied_concurrency = max_concurrency or self.config.throttle.max_concurrency
        applied_limit_rate = limit_rate or self.config.throttle.limit_rate
        throttle_label = f"{applied_concurrency} concurrent @ {applied_limit_rate or 'unbounded'}"

        profile = ThrottleProfile(
            max_concurrency=applied_concurrency,
            limit_rate=applied_limit_rate,
            sleep_interval=self.config.throttle.sleep_interval,
            ban_backoff_initial=self.config.throttle.ban_backoff_initial,
            ban_backoff_factor=self.config.throttle.ban_backoff_factor,
            ban_backoff_max=self.config.throttle.ban_backoff_max,
        )
        throttle = ThrottleController(profile)

        start = time.perf_counter()
        videos = list(self.enumerate_videos())
        completed_entries, skipped_records, failed_entries = self._download_videos(videos, throttle)
        elapsed = time.perf_counter() - start

        total = len(videos)
        skipped = len(skipped_records)
        completed = len(completed_entries)
        failed = len(failed_entries)
        pending = max(0, total - completed - skipped - failed)
        manifest = self._manifest_cache or {
            "playlistUrl": self.playlist_url,
            "title": self.playlist_url,
            "videos": videos,
        }

        return DownloadSummary(
            total=total,
            completed=completed,
            skipped=skipped,
            failed=failed,
            pending=pending,
            throttle_label=throttle_label,
            elapsed_seconds=elapsed,
            eta_seconds=self._calculate_eta(pending),
            applied_concurrency=applied_concurrency,
            applied_limit_rate=applied_limit_rate,
            sleep_interval=self.config.throttle.sleep_interval,
            throttle_metrics=throttle.metrics,
            skipped_items=tuple(skipped_records),
            manifest=manifest,
            completed_videos=tuple(self._entry_identifier(entry) for entry in completed_entries),
            pending_videos=tuple(self._entry_identifier(entry) for entry in failed_entries),
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

        profile = ThrottleProfile(
            max_concurrency=applied_concurrency,
            limit_rate=applied_limit_rate,
            sleep_interval=sleep_interval,
            ban_backoff_initial=self.config.throttle.ban_backoff_initial,
            ban_backoff_factor=self.config.throttle.ban_backoff_factor,
            ban_backoff_max=self.config.throttle.ban_backoff_max,
        )
        throttle = ThrottleController(profile)

        if checkpoint.manifest:
            self._manifest_cache = checkpoint.manifest

        manifest = checkpoint.manifest or self._load_manifest()
        manifest_videos = manifest.get("videos", [])
        manifest_lookup = {
            self._entry_identifier(entry): entry for entry in manifest_videos if entry
        }

        completed_urls = list(checkpoint.completed_videos)
        start = time.perf_counter()
        final_pending = list(checkpoint.pending_videos)
        if not final_pending and manifest_lookup:
            completed_set = set(completed_urls)
            final_pending = [
                identifier for identifier in manifest_lookup if identifier not in completed_set
            ]

        entries_to_download = [
            manifest_lookup.get(identifier, {"id": identifier, "url": identifier, "title": identifier})
            for identifier in final_pending
        ]

        completed_entries, skipped_records, failed_entries = self._download_videos(
            entries_to_download, throttle
        )
        elapsed = time.perf_counter() - start

        completed_urls.extend(self._entry_identifier(entry) for entry in completed_entries)
        failed = len(failed_entries)
        skipped = len(skipped_records)
        total_videos = len(manifest_videos) if manifest_videos else (
            len(checkpoint.completed_videos) + len(checkpoint.pending_videos)
        )

        return DownloadSummary(
            total=total_videos,
            completed=len(completed_urls),
            skipped=skipped,
            failed=failed,
            pending=0,
            throttle_label=throttle_label,
            elapsed_seconds=elapsed,
            eta_seconds=0.0,
            applied_concurrency=applied_concurrency,
            applied_limit_rate=applied_limit_rate,
            sleep_interval=sleep_interval,
            manifest=manifest,
            throttle_metrics=throttle.metrics,
            skipped_items=tuple(skipped_records),
            completed_videos=tuple(completed_urls),
            pending_videos=tuple(self._entry_identifier(entry) for entry in failed_entries),
        )


__all__ = ["DownloadSummary", "PlaylistDownloader", "SkipRecord"]
