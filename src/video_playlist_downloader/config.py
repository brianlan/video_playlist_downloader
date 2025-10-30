"""
Configuration loading utilities for the Video Playlist Downloader.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional dependency fallback
    def load_dotenv(*args, **kwargs):  # type: ignore[override]
        return False

DEFAULT_STORAGE_DIR = Path("video-storage")
DEFAULT_REPORTS_DIR = Path("reports")
DEFAULT_DATABASE_FILENAME = "state.db"
DEFAULT_MIN_FREE_GB = 1.0


@dataclass(frozen=True)
class StoragePaths:
    """Resolved filesystem locations used by the application."""

    root: Path
    downloads: Path
    database: Path
    reports: Path


@dataclass(frozen=True)
class ThrottleSettings:
    """Configuration for throttle and retry behavior."""

    max_concurrency: int = 2
    limit_rate: Optional[str] = None
    sleep_interval: float = 1.0
    max_retries: int = 3
    retry_backoff: float = 1.5


@dataclass(frozen=True)
class AppConfig:
    """Aggregate application configuration."""

    storage: StoragePaths
    throttle: ThrottleSettings
    subtitle_languages: tuple[str, ...] = field(default_factory=tuple)
    env_file: Optional[Path] = None
    minimum_free_gb: float = DEFAULT_MIN_FREE_GB


def _comma_separated_list(raw: Optional[str]) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(token.strip() for token in raw.split(",") if token.strip())


def _ensure_absolute(path: Path) -> Path:
    return path if path.is_absolute() else Path.cwd() / path


def load_config(dotenv_path: Optional[Path] = None) -> AppConfig:
    """
    Load configuration from the environment, optionally merging values from a dotenv file.
    """

    env_file = dotenv_path or Path(".env")
    if env_file.exists():
        load_dotenv(env_file, override=False)

    storage_root = _ensure_absolute(
        Path(os.getenv("VPD_STORAGE_ROOT", DEFAULT_STORAGE_DIR))
    )
    downloads_dir = storage_root / "downloads"
    database_path = storage_root / os.getenv("VPD_DATABASE_FILENAME", DEFAULT_DATABASE_FILENAME)
    reports_dir = _ensure_absolute(Path(os.getenv("VPD_REPORTS_DIR", DEFAULT_REPORTS_DIR)))

    throttle = ThrottleSettings(
        max_concurrency=int(os.getenv("VPD_MAX_CONCURRENCY", "2")),
        limit_rate=os.getenv("VPD_LIMIT_RATE"),
        sleep_interval=float(os.getenv("VPD_SLEEP_INTERVAL", "1.0")),
        max_retries=int(os.getenv("VPD_MAX_RETRIES", "3")),
        retry_backoff=float(os.getenv("VPD_RETRY_BACKOFF", "1.5")),
    )

    subtitle_languages = _comma_separated_list(os.getenv("VPD_SUBTITLE_LANGUAGES"))

    storage_paths = StoragePaths(
        root=storage_root,
        downloads=downloads_dir,
        database=database_path,
        reports=reports_dir,
    )

    minimum_free_gb = float(os.getenv("VPD_MIN_FREE_GB", str(DEFAULT_MIN_FREE_GB)))

    return AppConfig(
        storage=storage_paths,
        throttle=throttle,
        subtitle_languages=subtitle_languages,
        env_file=env_file if env_file.exists() else None,
        minimum_free_gb=minimum_free_gb,
    )


__all__ = ["AppConfig", "StoragePaths", "ThrottleSettings", "load_config", "DEFAULT_MIN_FREE_GB"]
