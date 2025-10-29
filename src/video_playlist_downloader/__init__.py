"""
Video Playlist Downloader package scaffolding.

Modules will be populated as implementation tasks progress.
"""

from importlib import metadata


def __getattr__(name: str) -> str:
    if name == "__version__":
        try:
            return metadata.version("video-playlist-downloader")
        except metadata.PackageNotFoundError:
            return "0.0.0"
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["__version__"]
