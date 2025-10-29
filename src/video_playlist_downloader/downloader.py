"""
Playlist download orchestration scaffolding.

Real download logic will be introduced in later tasks.
"""

from __future__ import annotations

from typing import Iterable


class PlaylistDownloader:
    """Placeholder downloader implementation."""

    def __init__(self, playlist_url: str) -> None:
        self.playlist_url = playlist_url

    def enumerate_videos(self) -> Iterable[str]:
        """Yield placeholder video identifiers."""
        return []

    def download(self) -> None:
        """Execute a no-op download."""
        return None
