"""
Command-line interface bootstrap for the Video Playlist Downloader.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from uuid import uuid4

import typer
from rich.console import Console

from .config import AppConfig, load_config
from .downloader import DownloadSummary, PlaylistDownloader
from .persistence import PersistenceConfig, configure_persistence, record_session_run
from .storage_guard import InsufficientStorageError, StorageGuard

app = typer.Typer(help="Download and manage playlist archives from Bilibili.")
console = Console()
err_console = Console(stderr=True)


@dataclass(frozen=True)
class StatusSnapshot:
    """Rendered data for the status command."""

    playlist_url: str
    total: int
    completed: int
    skipped: int
    failed: int
    pending: int
    throttle_label: str
    elapsed_seconds: float
    eta_seconds: float


def _load_configuration(config_file: Optional[Path]) -> AppConfig:
    return load_config(config_file)


def _ensure_storage_paths(config: AppConfig) -> None:
    storage = config.storage
    storage.root.mkdir(parents=True, exist_ok=True)
    storage.downloads.mkdir(parents=True, exist_ok=True)
    storage.database.parent.mkdir(parents=True, exist_ok=True)
    storage.reports.mkdir(parents=True, exist_ok=True)


def _configure_database(config: AppConfig) -> None:
    persistence_config = PersistenceConfig(database_path=config.storage.database)
    configure_persistence(persistence_config)


def _render_download_summary(summary: DownloadSummary) -> None:
    console.print("[bold cyan]Download Summary[/bold cyan]")
    console.print(f"Totals: {summary.total}")
    console.print(f"Completed: {summary.completed}")
    console.print(f"Skipped: {summary.skipped}")
    console.print(f"Failed: {summary.failed}")
    console.print(f"Pending: {summary.pending}")
    console.print(f"Throttle: {summary.throttle_label}")
    console.print(f"Elapsed: {summary.elapsed_seconds:.1f}s")
    console.print(f"ETA: {summary.eta_seconds:.1f}s")


def _render_status(snapshot: StatusSnapshot) -> None:
    console.print("[bold cyan]Playlist Status[/bold cyan]")
    console.print(f"Playlist: {snapshot.playlist_url}")
    console.print(f"Total Videos: {snapshot.total}")
    console.print(f"Completed: {snapshot.completed}")
    console.print(f"Skipped: {snapshot.skipped}")
    console.print(f"Failed: {snapshot.failed}")
    console.print(f"Pending: {snapshot.pending}")
    console.print(f"Throttle: {snapshot.throttle_label}")
    console.print(f"Elapsed: {snapshot.elapsed_seconds:.1f}s")
    console.print(f"ETA: {snapshot.eta_seconds:.1f}s")


def _collect_status_snapshot(config: AppConfig, playlist_url: str) -> StatusSnapshot:
    """
    Lookup the latest status information for the requested playlist.

    The current implementation returns placeholder data that will be replaced once
    persistence models are available.
    """

    return StatusSnapshot(
        playlist_url=playlist_url,
        total=0,
        completed=0,
        skipped=0,
        failed=0,
        pending=0,
        throttle_label=f"{config.throttle.max_concurrency} concurrent @ "
        f"{config.throttle.limit_rate or 'unbounded'}",
        elapsed_seconds=0.0,
        eta_seconds=0.0,
    )


@app.callback()
def main(
    ctx: typer.Context,
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to an optional .env file with configuration overrides.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
) -> None:
    """
    Initialize shared CLI context with configuration and Rich consoles.
    """

    ctx.obj = {
        "config": _load_configuration(config_file),
        "console": console,
        "err_console": err_console,
    }


@app.command()
def download(
    ctx: typer.Context,
    playlist_url: str = typer.Argument(..., help="Playlist URL to download."),
    max_concurrency: Optional[int] = typer.Option(
        None,
        "--max-concurrency",
        min=1,
        help="Override default maximum concurrent downloads.",
    ),
    limit_rate: Optional[str] = typer.Option(
        None,
        "--limit-rate",
        help="Network rate limit (e.g., 2M, 500K).",
    ),
) -> None:
    """
    Download an entire playlist using configured settings.
    """

    config: AppConfig = ctx.obj["config"]

    _ensure_storage_paths(config)

    storage_guard = StorageGuard.from_gigabytes(config.minimum_free_gb)
    try:
        storage_guard.ensure_capacity(config.storage.downloads)
    except InsufficientStorageError as exc:
        import sys

        message = str(exc)
        print(message, file=sys.stderr)
        typer.echo(typer.style(message, fg=typer.colors.RED), err=True)
        raise typer.Exit(code=1) from exc

    _configure_database(config)

    downloader = PlaylistDownloader(
        config=config,
        playlist_url=playlist_url,
    )
    summary = downloader.run(
        max_concurrency=max_concurrency,
        limit_rate=limit_rate,
    )
    session_id = str(uuid4())

    record_session_run(
        config.storage.database,
        session_id=session_id,
        playlist_url=playlist_url,
        summary=summary,
    )

    _render_download_summary(summary)
    console.print(f"Session ID: {session_id}")


@app.command()
def status(
    ctx: typer.Context,
    playlist_url: str = typer.Option(
        ...,
        "--playlist-url",
        help="Playlist URL to query.",
    ),
) -> None:
    """
    Display stored download status for a playlist.
    """

    config: AppConfig = ctx.obj["config"]
    snapshot = _collect_status_snapshot(config, playlist_url)
    _render_status(snapshot)


@app.command()
def resume(
    ctx: typer.Context,
    session_id: str = typer.Argument(..., help="Session identifier to resume."),
) -> None:
    """
    Resume a previously interrupted download session.

    Placeholder implementation, full resume workflow will arrive in User Story 2.
    """

    console.print(f"[yellow]Resume requested for session {session_id}[/yellow]")


@app.command()
def version() -> None:
    """Display scaffold placeholder version information."""
    from . import __version__

    console.print(f"video-playlist-downloader {__version__}")


def main_entry() -> None:
    """Entrypoint for console scripts."""
    app()


if __name__ == "__main__":
    main_entry()
