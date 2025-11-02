#!/usr/bin/env python3

"""
Provision storage directories required by the Video Playlist Downloader.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from video_playlist_downloader.config import AppConfig, load_config

console = Console()


def _ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _initialize_storage(config: AppConfig) -> None:
    _ensure_directory(config.storage.root)
    _ensure_directory(config.storage.downloads)
    _ensure_directory(config.storage.database.parent)
    _ensure_directory(config.storage.reports)
    config.storage.database.touch(exist_ok=True)


def main() -> None:
    config = load_config()
    _initialize_storage(config)
    console.print(
        "[green]Storage initialized at[/green] "
        f"{config.storage.root} (database: {config.storage.database})"
    )


if __name__ == "__main__":
    main()
