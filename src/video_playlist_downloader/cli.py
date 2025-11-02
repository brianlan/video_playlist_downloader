"""
Command-line interface bootstrap for the Video Playlist Downloader.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, Literal, Optional
from uuid import NAMESPACE_URL, uuid4, uuid5

import typer
from rich.console import Console

from .config import AppConfig, load_config
from .downloader import DownloadSummary, PlaylistDownloader
from .persistence import (
    PersistenceConfig,
    ResumeCheckpoint,
    configure_persistence,
    fetch_playlist_sessions,
    persist_metadata_summary,
    load_resume_checkpoint,
    record_session_run,
    save_playlist_manifest,
    save_resume_checkpoint,
)
from .storage_guard import InsufficientStorageError, StorageGuard

app = typer.Typer(help="Download and manage playlist archives from Bilibili.")
console = Console()
err_console = Console(stderr=True)
logger = logging.getLogger("video_playlist_downloader.cli")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(handler)
logger.propagate = False

OUTPUT_FORMATS = ("text", "json")
_REDACTION_PATTERN = re.compile(r"(token|key|secret|session_id)=([^&\s]+)", re.IGNORECASE)


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


def _derive_playlist_id(playlist_url: str) -> str:
    return str(uuid5(NAMESPACE_URL, playlist_url))


def _redact_sensitive(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return _REDACTION_PATTERN.sub(lambda m: f"{m.group(1)}=***", value)


def _append_quality_summary(
    config: AppConfig,
    *,
    session_id: str,
    playlist_id: str,
    summary: DownloadSummary,
) -> None:
    report_path = config.storage.reports / "quality-summary.md"
    if not report_path.exists():
        report_path.write_text(
            "# Quality Summary\n\n"
            "| Session ID | Playlist ID | Total | Completed | Skipped | Failed | Elapsed (s) |\n"
            "|------------|-------------|-------|-----------|---------|--------|-------------|\n"
        )
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write(
            f"| {session_id} | {playlist_id} | {summary.total} | {summary.completed} | "
            f"{summary.skipped} | {summary.failed} | {summary.elapsed_seconds:.2f} |\n"
        )


def _append_throttle_metrics_report(
    config: AppConfig,
    *,
    session_id: str,
    playlist_id: str,
    summary: DownloadSummary,
) -> None:
    """Append throttle metrics for the run to the report file."""

    metrics = summary.throttle_metrics
    report_path = config.storage.reports / "throttle-metrics.md"
    if not report_path.exists():
        report_path.write_text(
            "# Throttle Metrics\n\n"
            "| Session ID | Playlist ID | Compliance | Ban events | Sleep (s) | Backoff (s) |\n"
            "|------------|-------------|------------|------------|-----------|-------------|\n",
            encoding="utf-8",
        )
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write(
            f"| {session_id} | {playlist_id} | {metrics.compliance_ratio * 100:.2f}% | "
            f"{metrics.ban_events} | {metrics.total_sleep_seconds:.2f} | "
            f"{metrics.total_backoff_seconds:.2f} |\n"
        )


def _write_subtitle_report(config: AppConfig, coverage: Dict[str, Any]) -> None:
    report_path = config.storage.reports / "subtitle-metrics.json"
    report_path.write_text(json.dumps(coverage, indent=2), encoding="utf-8")


def _build_throttle_profile(summary: DownloadSummary) -> Dict[str, Any]:
    return {
        "maxConcurrency": summary.applied_concurrency,
        "limitRate": summary.applied_limit_rate,
        "sleepIntervalSeconds": summary.sleep_interval,
    }


def _persist_resume_checkpoint(
    config: AppConfig,
    *,
    session_id: str,
    playlist_id: str,
    playlist_url: str,
    summary: DownloadSummary,
    resumed_from: Optional[str] = None,
) -> None:
    checkpoint = ResumeCheckpoint(
        session_id=session_id,
        playlist_id=playlist_id,
        playlist_url=playlist_url,
        completed_videos=tuple(summary.completed_videos),
        pending_videos=tuple(summary.pending_videos),
        throttle_profile=_build_throttle_profile(summary),
        resumed_from=resumed_from,
        manifest=summary.manifest,
    )
    save_resume_checkpoint(config.storage.database, checkpoint)


def _persist_metadata_from_summary(
    config: AppConfig,
    *,
    playlist_id: str,
    playlist_url: str,
    summary: DownloadSummary,
) -> Optional[Dict[str, Any]]:
    coverage = persist_metadata_summary(
        config.storage.database,
        playlist_id=playlist_id,
        playlist_url=playlist_url,
        summary=summary,
    )
    if coverage:
        _write_subtitle_report(config, coverage)
    return coverage


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
    metrics = summary.throttle_metrics
    console.print(f"Throttle compliance: {metrics.compliance_ratio * 100:.2f}%")
    console.print(f"Ban events: {metrics.ban_events}")


def _render_status(snapshot: StatusSnapshot) -> None:
    console.print("[bold cyan]Playlist Status[/bold cyan]")
    safe_url = _redact_sensitive(snapshot.playlist_url) or snapshot.playlist_url
    console.print(f"Playlist: {safe_url}")
    console.print(f"Total Videos: {snapshot.total}")
    console.print(f"Completed: {snapshot.completed}")
    console.print(f"Skipped: {snapshot.skipped}")
    console.print(f"Failed: {snapshot.failed}")
    console.print(f"Pending: {snapshot.pending}")
    console.print(f"Throttle: {snapshot.throttle_label}")
    console.print(f"Elapsed: {snapshot.elapsed_seconds:.1f}s")
    console.print(f"ETA: {snapshot.eta_seconds:.1f}s")


def _collect_status_snapshot(config: AppConfig, playlist_url: str) -> StatusSnapshot:
    sessions = fetch_playlist_sessions(config.storage.database, playlist_url)
    return _snapshot_from_sessions(config, playlist_url, sessions)


def _snapshot_from_sessions(
    config: AppConfig, playlist_url: str, sessions: list[dict[str, Any]]
) -> StatusSnapshot:
    if not sessions:
        return StatusSnapshot(
            playlist_url=playlist_url,
            total=0,
            completed=0,
            skipped=0,
            failed=0,
            pending=0,
            throttle_label=
            f"{config.throttle.max_concurrency} concurrent @ "
            f"{config.throttle.limit_rate or 'unbounded'}",
            elapsed_seconds=0.0,
            eta_seconds=0.0,
        )

    latest = sessions[0]
    throttle_label = latest.get("throttle_label") or (
        f"{latest.get('throttle_max_concurrency') or config.throttle.max_concurrency} "
        f"concurrent @ {latest.get('throttle_limit_rate') or config.throttle.limit_rate or 'unbounded'}"
    )
    return StatusSnapshot(
        playlist_url=playlist_url,
        total=int(latest.get("total", 0)),
        completed=int(latest.get("completed", 0)),
        skipped=int(latest.get("skipped", 0)),
        failed=int(latest.get("failed", 0)),
        pending=int(latest.get("pending", 0)),
        throttle_label=throttle_label,
        elapsed_seconds=float(latest.get("elapsed_seconds", 0.0)),
        eta_seconds=float(latest.get("eta_seconds", 0.0)),
    )


def _build_download_contract_payload(
    *,
    session_id: str,
    playlist_id: str,
    summary: DownloadSummary,
) -> dict[str, Any]:
    return {
        "sessionId": session_id,
        "playlistId": playlist_id,
        "enqueued": summary.total,
        "throttle": summary.throttle_metrics.to_dict(),
    }


def _build_status_contract_payload(
    *,
    playlist_id: str,
    sessions: list[dict[str, Any]],
    config: AppConfig,
) -> dict[str, Any]:
    if not sessions:
        throttle_profile = {
            "maxConcurrency": config.throttle.max_concurrency,
            "limitRate": config.throttle.limit_rate,
            "sleepIntervalSeconds": config.throttle.sleep_interval,
        }
        session_payloads: list[dict[str, Any]] = []
    else:
        session_payloads = []
        for row in sessions:
            session_payloads.append(
                {
                    "sessionId": row["session_id"],
                    "status": row.get("status", "completed"),
                    "videosTotal": row.get("total", 0),
                    "videosCompleted": row.get("completed", 0),
                    "videosSkipped": row.get("skipped", 0),
                    "videosFailed": row.get("failed", 0),
                    "throttleProfile": {
                        "maxConcurrency": row.get("throttle_max_concurrency")
                        or config.throttle.max_concurrency,
                        "limitRate": row.get("throttle_limit_rate")
                        or config.throttle.limit_rate,
                        "sleepIntervalSeconds": row.get("throttle_sleep_interval")
                        or config.throttle.sleep_interval,
                    },
                }
            )
        throttle_profile = session_payloads[0]["throttleProfile"]

    return {
        "playlistId": playlist_id,
        "sessions": session_payloads,
        "throttleProfile": throttle_profile,
    }


def _build_resume_contract_payload(
    *,
    session_id: str,
    resumed_from: str,
    playlist_id: str,
    summary: DownloadSummary,
) -> dict[str, Any]:
    return {
        "sessionId": session_id,
        "resumedFrom": resumed_from,
        "playlistId": playlist_id,
        "videosTotal": summary.total,
        "videosCompleted": summary.completed,
        "videosSkipped": summary.skipped,
        "videosFailed": summary.failed,
        "throttleProfile": {
            "maxConcurrency": summary.applied_concurrency,
            "limitRate": summary.applied_limit_rate,
            "sleepIntervalSeconds": summary.sleep_interval,
        },
    }


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
    output_format: Literal["text", "json"] = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format for command results.",
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
    playlist_id = _derive_playlist_id(playlist_url)

    record_session_run(
        config.storage.database,
        session_id=session_id,
        playlist_id=playlist_id,
        playlist_url=playlist_url,
        summary=summary,
    )

    if summary.manifest is not None:
        save_playlist_manifest(config.storage.database, playlist_id, summary.manifest)

    _append_quality_summary(
        config,
        session_id=session_id,
        playlist_id=playlist_id,
        summary=summary,
    )
    _append_throttle_metrics_report(
        config,
        session_id=session_id,
        playlist_id=playlist_id,
        summary=summary,
    )

    coverage = _persist_metadata_from_summary(
        config,
        playlist_id=playlist_id,
        playlist_url=playlist_url,
        summary=summary,
    )

    if coverage:
        console.print(
            f"Subtitle Coverage: {coverage['coveragePercent']}% "
            f"({coverage['videosWithSubtitles']}/{coverage['totalVideos']})"
        )

    compliance_ratio = summary.throttle_metrics.compliance_ratio
    logger.info(
        "Session %s throttle compliance %.2f%% (ban events=%s)",
        session_id,
        compliance_ratio * 100,
        summary.throttle_metrics.ban_events,
    )
    if compliance_ratio < config.throttle.compliance_threshold:
        err_console.print(
            typer.style(
                f"Throttle compliance {compliance_ratio * 100:.2f}% "
                f"is below threshold ({config.throttle.compliance_threshold * 100:.2f}%).",
                fg=typer.colors.RED,
            )
        )
        logger.warning(
            "Compliance below threshold for session %s (%.2f%% < %.2f%%)",
            session_id,
            compliance_ratio * 100,
            config.throttle.compliance_threshold * 100,
        )

    if output_format == "json":
        payload = _build_download_contract_payload(
            session_id=session_id,
            playlist_id=playlist_id,
            summary=summary,
        )
        typer.echo(json.dumps(payload))
    else:
        _render_download_summary(summary)
        console.print(f"Session ID: {session_id}")
    _persist_resume_checkpoint(
        config,
        session_id=session_id,
        playlist_id=playlist_id,
        playlist_url=playlist_url,
        summary=summary,
    )


@app.command()
def status(
    ctx: typer.Context,
    playlist_url: str = typer.Option(
        ...,
        "--playlist-url",
        help="Playlist URL to query.",
    ),
    output_format: Literal["text", "json"] = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format for command results.",
    ),
) -> None:
    """
    Display stored download status for a playlist.
    """

    config: AppConfig = ctx.obj["config"]
    playlist_id = _derive_playlist_id(playlist_url)
    sessions = fetch_playlist_sessions(config.storage.database, playlist_url)
    if output_format == "json":
        payload = _build_status_contract_payload(
            playlist_id=playlist_id,
            sessions=sessions,
            config=config,
        )
        typer.echo(json.dumps(payload))
    else:
        snapshot = _snapshot_from_sessions(config, playlist_url, sessions)
        _render_status(snapshot)


@app.command()
def resume(
    ctx: typer.Context,
    session_id: str = typer.Argument(..., help="Session identifier to resume."),
    output_format: Literal["text", "json"] = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format for command results.",
    ),
) -> None:
    """
    Resume a previously interrupted download session.
    """

    config: AppConfig = ctx.obj["config"]
    _ensure_storage_paths(config)
    _configure_database(config)

    checkpoint: Optional[ResumeCheckpoint] = load_resume_checkpoint(
        config.storage.database, session_id
    )
    if checkpoint is None:
        typer.echo(
            typer.style(f"No checkpoint found for session {session_id}", fg=typer.colors.RED),
            err=True,
        )
        raise typer.Exit(code=1)

    downloader = PlaylistDownloader(
        config=config,
        playlist_url=checkpoint.playlist_url,
    )
    summary = downloader.resume_from_checkpoint(checkpoint)
    new_session_id = str(uuid4())

    record_session_run(
        config.storage.database,
        session_id=new_session_id,
        playlist_id=checkpoint.playlist_id,
        playlist_url=checkpoint.playlist_url,
        summary=summary,
        status="resumed",
    )

    _append_quality_summary(
        config,
        session_id=new_session_id,
        playlist_id=checkpoint.playlist_id,
        summary=summary,
    )

    if summary.manifest is not None:
        save_playlist_manifest(
            config.storage.database,
            checkpoint.playlist_id,
            summary.manifest,
        )

    coverage = _persist_metadata_from_summary(
        config,
        playlist_id=checkpoint.playlist_id,
        playlist_url=checkpoint.playlist_url,
        summary=summary,
    )

    if coverage:
        console.print(
            f"Subtitle Coverage: {coverage['coveragePercent']}% "
            f"({coverage['videosWithSubtitles']}/{coverage['totalVideos']})"
        )

    if output_format == "json":
        payload = _build_resume_contract_payload(
            session_id=new_session_id,
            resumed_from=session_id,
            playlist_id=checkpoint.playlist_id,
            summary=summary,
        )
        typer.echo(json.dumps(payload))
    else:
        _render_download_summary(summary)
        console.print(
            f"Session ID: {new_session_id} (resumed from {session_id})"
        )
    _persist_resume_checkpoint(
        config,
        session_id=new_session_id,
        playlist_id=checkpoint.playlist_id,
        playlist_url=checkpoint.playlist_url,
        summary=summary,
        resumed_from=session_id,
    )


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
