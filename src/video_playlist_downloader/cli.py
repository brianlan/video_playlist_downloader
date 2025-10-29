"""
Command-line interface bootstrap for the Video Playlist Downloader.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .config import AppConfig, load_config

app = typer.Typer(help="Download and manage playlist archives from Bilibili.")
console = Console()
err_console = Console(stderr=True)


def _load_configuration(config_file: Optional[Path]) -> AppConfig:
    return load_config(config_file)


def _render_placeholder(message: str) -> None:
    console.print(f"[cyan]{message}[/cyan]")


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
    _render_placeholder(
        f"Download command invoked for {playlist_url} with database {config.storage.database}"
    )
    if max_concurrency:
        _render_placeholder(f"Max concurrency override: {max_concurrency}")
    if limit_rate:
        _render_placeholder(f"Limit rate override: {limit_rate}")


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

    _render_placeholder(f"Status requested for {playlist_url}")


@app.command()
def resume(
    ctx: typer.Context,
    session_id: str = typer.Argument(..., help="Session identifier to resume."),
) -> None:
    """
    Resume a previously interrupted download session.
    """

    _render_placeholder(f"Resume requested for session {session_id}")


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
