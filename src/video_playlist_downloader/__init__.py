"""
Video Playlist Downloader package scaffolding.

Modules will be populated as implementation tasks progress.
"""

from importlib import metadata as importlib_metadata

from . import metadata as metadata_module
from . import subtitles as subtitles_module


def __getattr__(name: str) -> str:
    if name == "__version__":
        try:
            return importlib_metadata.version("video-playlist-downloader")
        except importlib_metadata.PackageNotFoundError:
            return "0.0.0"
    if name == "metadata":
        return metadata_module
    if name == "subtitles":
        return subtitles_module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["__version__", "metadata", "subtitles"]
