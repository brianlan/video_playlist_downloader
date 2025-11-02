from __future__ import annotations

from typing import Iterable, List, Sequence

from video_playlist_downloader.downloader import DownloadSummary, PlaylistDownloader
from video_playlist_downloader.persistence import ResumeCheckpoint


def _make_entries() -> List[dict[str, object]]:
    return [
        {
            "id": "video-a",
            "title": "Video A",
            "webpage_url": "https://example.com/video-a",
            "duration": 120,
            "bvid": "BV1",
        },
        {
            "id": "video-b",
            "title": "Video B",
            "webpage_url": "https://example.com/video-b",
            "availability": "premium_only",
            "duration": 180,
            "bvid": "BV2",
        },
        {
            "id": "video-c",
            "title": "Video C",
            "webpage_url": "https://example.com/video-c",
            "duration": 240,
            "bvid": "BV3",
        },
    ]


class StubYtDlp:
    def __init__(self, entries: Sequence[dict[str, object]]) -> None:
        self._entries = list(entries)
        self.extract_calls: List[tuple[str, bool]] = []
        self.download_calls: List[Iterable[str]] = []

    def extract_info(self, url: str, download: bool = False) -> dict[str, object]:
        self.extract_calls.append((url, download))
        return {
            "id": "playlist-xyz",
            "title": "Example Playlist",
            "entries": list(self._entries),
        }

    def download(self, urls: Iterable[str]) -> None:
        self.download_calls.append(tuple(urls))


class RecordingDownloader(PlaylistDownloader):
    def __init__(self, *, yt_client: StubYtDlp, **kwargs) -> None:
        super().__init__(yt_dlp_client=yt_client, **kwargs)
        self.client = yt_client
        self.attempted: List[str] = []

    def _perform_download(self, entry: dict[str, object]) -> bool:
        url = entry["url"]  # type: ignore[index]
        self.attempted.append(url)
        self.client.download([url])
        # Simulate a failure for the last entry to exercise retry bookkeeping.
        return not url.endswith("video-c")


class ResumeDownloader(PlaylistDownloader):
    def __init__(self, *, yt_client: StubYtDlp, **kwargs) -> None:
        super().__init__(yt_dlp_client=yt_client, **kwargs)
        self.client = yt_client

    def _perform_download(self, entry: dict[str, object]) -> bool:
        url = entry["url"]  # type: ignore[index]
        self.client.download([url])
        return True


def test_run_collects_manifest_and_skip_records(app_config):
    client = StubYtDlp(_make_entries())
    downloader = RecordingDownloader(
        config=app_config,
        playlist_url="https://example.com/playlist",
        yt_client=client,
    )

    summary: DownloadSummary = downloader.run()

    assert summary.total == 3
    assert summary.completed == 1
    assert summary.failed == 1
    assert summary.skipped == 1
    assert summary.pending == 0

    assert summary.completed_videos == ("https://example.com/video-a",)
    assert summary.pending_videos == ("https://example.com/video-c",)

    assert len(summary.skipped_items) == 1
    skip = summary.skipped_items[0]
    assert skip.video_url == "https://example.com/video-b"
    assert "premium" in skip.reason.lower()

    assert summary.manifest is not None
    assert summary.manifest["title"] == "Example Playlist"
    videos = summary.manifest["videos"]
    assert isinstance(videos, list)
    assert videos[0]["url"] == "https://example.com/video-a"

    assert client.extract_calls == [("https://example.com/playlist", False)]
    assert client.download_calls == [
        ("https://example.com/video-a",),
        ("https://example.com/video-c",),
    ]
    assert summary.throttle_metrics.total_requests == 2


def test_resume_rehydrates_pending_videos_from_manifest(app_config):
    client = StubYtDlp(_make_entries())
    downloader = ResumeDownloader(
        config=app_config,
        playlist_url="https://example.com/playlist",
        yt_client=client,
    )

    manifest_videos = downloader.enumerate_videos()
    manifest = {
        "playlistUrl": "https://example.com/playlist",
        "title": "Example Playlist",
        "videos": manifest_videos,
    }

    checkpoint = ResumeCheckpoint(
        session_id="session-123",
        playlist_id="playlist-xyz",
        playlist_url="https://example.com/playlist",
        completed_videos=("https://example.com/video-a",),
        pending_videos=(),
        throttle_profile={
            "maxConcurrency": 2,
            "limitRate": None,
            "sleepIntervalSeconds": 1.0,
        },
        resumed_from=None,
        manifest=manifest,
    )

    summary = downloader.resume_from_checkpoint(checkpoint)

    assert summary.total == 3
    assert summary.completed == 2
    assert summary.skipped == 1
    assert summary.failed == 0
    assert summary.pending == 0
    assert summary.completed_videos == (
        "https://example.com/video-a",
        "https://example.com/video-c",
    )
    assert not summary.pending_videos

    # One download should occur for the remaining video.
    assert client.download_calls == [("https://example.com/video-c",)]
