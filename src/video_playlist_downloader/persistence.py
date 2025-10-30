"""
SQLite persistence initialization utilities.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import sqlite3
from pathlib import Path
import time
from typing import Any, Dict, Iterator, Optional, Tuple
from types import SimpleNamespace

try:
    from sqlalchemy import Engine, create_engine  # type: ignore
    from sqlalchemy import exc as sa_exc  # type: ignore
    from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker  # type: ignore
    _SQLALCHEMY_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - optional dependency fallback
    Engine = Any  # type: ignore
    Session = Any  # type: ignore

    class _OperationalError(RuntimeError):
        ...

    class DeclarativeBase:  # type: ignore
        pass

    def create_engine(*args: Any, **kwargs: Any) -> Any:  # type: ignore
        raise RuntimeError("SQLAlchemy is required to use persistence features.")

    class _SessionMaker:
        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("SQLAlchemy is required to create sessions.")

    sessionmaker = _SessionMaker()  # type: ignore

    sa_exc = type("sa_exc", (), {"OperationalError": _OperationalError})  # type: ignore
    _SQLALCHEMY_AVAILABLE = False

try:
    from tenacity import (  # type: ignore
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential_jitter,
    )
except ModuleNotFoundError:  # pragma: no cover - optional dependency fallback

    def retry(*args: Any, **kwargs: Any):  # type: ignore
        def decorator(func):
            return func

        return decorator

    def retry_if_exception_type(*args: Any, **kwargs: Any):  # type: ignore
        return lambda exc: False

    def stop_after_attempt(*args: Any, **kwargs: Any):  # type: ignore
        return None

    def wait_exponential_jitter(*args: Any, **kwargs: Any):  # type: ignore
        return None


if _SQLALCHEMY_AVAILABLE:

    class Base(DeclarativeBase):
        """Declarative base for ORM models."""

else:

    class Base:  # type: ignore[misc]
        """Fallback base used when SQLAlchemy is unavailable."""

        metadata = SimpleNamespace(create_all=lambda *args, **kwargs: None)

from . import metadata as metadata_module
from .downloader import DownloadSummary

_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS session_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        playlist_id TEXT NOT NULL,
        playlist_url TEXT NOT NULL,
        status TEXT NOT NULL,
        total INTEGER NOT NULL,
        completed INTEGER NOT NULL,
        skipped INTEGER NOT NULL,
        failed INTEGER NOT NULL,
        pending INTEGER NOT NULL,
        throttle_label TEXT NOT NULL,
        throttle_max_concurrency INTEGER,
        throttle_limit_rate TEXT,
        throttle_sleep_interval REAL,
        elapsed_seconds REAL NOT NULL,
        eta_seconds REAL NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS session_skips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        video_url TEXT NOT NULL,
        reason TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS resume_checkpoints (
        session_id TEXT PRIMARY KEY,
        playlist_id TEXT NOT NULL,
        playlist_url TEXT NOT NULL,
        completed_videos TEXT NOT NULL,
        pending_videos TEXT NOT NULL,
        throttle_profile TEXT NOT NULL,
        resumed_from TEXT,
        manifest TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS playlist_manifests (
        playlist_id TEXT PRIMARY KEY,
        manifest TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
]


@dataclass(frozen=True)
class ResumeCheckpoint:
    session_id: str
    playlist_id: str
    playlist_url: str
    completed_videos: Tuple[str, ...]
    pending_videos: Tuple[str, ...]
    throttle_profile: Dict[str, Any]
    resumed_from: Optional[str] = None
    manifest: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class PersistenceConfig:
    """Configuration describing how to connect to the application database."""

    database_path: Path
    echo: bool = False


_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker[Session]] = None


def _build_engine(database_path: Path, echo: bool = False) -> Optional[Engine]:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if not _SQLALCHEMY_AVAILABLE:
        return None
    return create_engine(
        f"sqlite:///{database_path}",
        echo=echo,
        future=True,
    )


def configure_persistence(config: PersistenceConfig) -> None:
    """
    Initialize the global SQLAlchemy engine and session factory.
    """

    global _engine, _session_factory

    engine = _build_engine(config.database_path, echo=config.echo)
    config.database_path.touch(exist_ok=True)
    _initialize_sqlite_schema(config.database_path)
    if engine is None:
        _engine = None
        _session_factory = None
        return

    Base.metadata.create_all(engine)

    _engine = engine
    _session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )


def get_engine() -> Engine:
    if not _SQLALCHEMY_AVAILABLE:
        raise RuntimeError("SQLAlchemy is required to access the engine.")
    if _engine is None:
        raise RuntimeError("Persistence not configured. Call configure_persistence() first.")
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if not _SQLALCHEMY_AVAILABLE:
        raise RuntimeError("SQLAlchemy is required to create sessions.")
    if _session_factory is None:
        raise RuntimeError("Persistence not configured. Call configure_persistence() first.")
    return _session_factory


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=0.1, max=1.0),
    retry=retry_if_exception_type(sa_exc.OperationalError),
)
def _commit_with_retry(session: Session) -> None:
    session.commit()


@contextmanager
def session_scope() -> Iterator[Session]:
    """
    Provide a transactional scope around a series of operations.
    """

    factory = get_session_factory()
    session = factory()
    try:
        yield session
        _commit_with_retry(session)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _initialize_sqlite_schema(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)
    try:
        for statement in _SCHEMA_STATEMENTS:
            connection.execute(statement)
        _ensure_schema_columns(connection)
        connection.commit()
    finally:
        connection.close()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def metadata_session_scope() -> Iterator[Optional[Session]]:
    if not (metadata_module.SQLALCHEMY_AVAILABLE and _SQLALCHEMY_AVAILABLE):
        yield None
        return

    engine = get_engine()
    metadata_module.create_metadata_schema(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _ensure_schema_columns(connection: sqlite3.Connection) -> None:
    cursor = connection.execute("PRAGMA table_info(session_activity)")
    rows = list(cursor) if hasattr(cursor, "__iter__") else []
    columns = {row[1]: row for row in rows}
    required_columns = {
        "playlist_id": "TEXT",
        "status": "TEXT",
        "throttle_max_concurrency": "INTEGER",
        "throttle_limit_rate": "TEXT",
        "throttle_sleep_interval": "REAL",
    }
    for name, column_type in required_columns.items():
        if name not in columns:
            connection.execute(
                f"ALTER TABLE session_activity ADD COLUMN {name} {column_type}"
            )

    # Ensure resume_checkpoints table exists
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS resume_checkpoints (
            session_id TEXT PRIMARY KEY,
            playlist_id TEXT NOT NULL,
            playlist_url TEXT NOT NULL,
            completed_videos TEXT NOT NULL,
            pending_videos TEXT NOT NULL,
            throttle_profile TEXT NOT NULL,
            resumed_from TEXT,
            manifest TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS playlist_manifests (
            playlist_id TEXT PRIMARY KEY,
            manifest TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )



def record_session_run(
    database_path: Path,
    *,
    session_id: str,
    playlist_id: str,
    playlist_url: str,
    summary: DownloadSummary,
    status: str = "completed",
) -> None:
    """
    Persist a completed session summary and any associated skip records.
    """

    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            """
            INSERT INTO session_activity (
                session_id,
                playlist_id,
                playlist_url,
                status,
                total,
                completed,
                skipped,
                failed,
                pending,
                throttle_label,
                throttle_max_concurrency,
                throttle_limit_rate,
                throttle_sleep_interval,
                elapsed_seconds,
                eta_seconds,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                playlist_id,
                playlist_url,
                status,
                summary.total,
                summary.completed,
                summary.skipped,
                summary.failed,
                summary.pending,
                summary.throttle_label,
                summary.applied_concurrency,
                summary.applied_limit_rate,
                summary.sleep_interval,
                summary.elapsed_seconds,
                summary.eta_seconds,
                _utc_now_iso(),
            ),
        )

        if summary.skipped_items:
            connection.executemany(
                """
                INSERT INTO session_skips (
                    session_id,
                    video_url,
                    reason,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    (
                        session_id,
                        skip.video_url,
                        skip.reason,
                        _utc_now_iso(),
                    )
                    for skip in summary.skipped_items
                ),
            )

        connection.commit()
    finally:
        connection.close()


def fetch_playlist_sessions(database_path: Path, playlist_url: str) -> list[dict[str, Any]]:
    """Return recorded session summaries for a playlist ordered from newest to oldest."""

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT
                session_id,
                playlist_id,
                status,
                total,
                completed,
                skipped,
                failed,
                pending,
                throttle_max_concurrency,
                throttle_limit_rate,
                throttle_sleep_interval,
                throttle_label,
                elapsed_seconds,
                eta_seconds,
                created_at
            FROM session_activity
            WHERE playlist_url = ?
            ORDER BY datetime(created_at) DESC
            """,
            (playlist_url,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def save_playlist_manifest(
    database_path: Path, playlist_id: str, manifest: Dict[str, Any]
) -> None:
    _initialize_sqlite_schema(database_path)
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            """
            INSERT INTO playlist_manifests (
                playlist_id,
                manifest,
                updated_at
            )
            VALUES (?, ?, ?)
            ON CONFLICT(playlist_id) DO UPDATE SET
                manifest = excluded.manifest,
                updated_at = excluded.updated_at
            """,
            (
                playlist_id,
                json.dumps(manifest),
                _utc_now_iso(),
            ),
        )
        connection.commit()
    finally:
        connection.close()


def load_playlist_manifest(
    database_path: Path, playlist_id: str
) -> Optional[Dict[str, Any]]:
    _initialize_sqlite_schema(database_path)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            "SELECT manifest FROM playlist_manifests WHERE playlist_id = ?",
            (playlist_id,),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["manifest"])
    finally:
        connection.close()


def persist_metadata_summary(
    database_path: Path,
    *,
    playlist_id: str,
    playlist_url: str,
    summary: DownloadSummary,
) -> Optional[Dict[str, Any]]:
    if not (metadata_module.SQLALCHEMY_AVAILABLE and _SQLALCHEMY_AVAILABLE):
        return None
    if summary.manifest is None:
        return None

    videos = summary.manifest.get("videos", [])
    manifest_title = summary.manifest.get("title", playlist_url)

    with metadata_session_scope() as session:
        if session is None:
            return None
        repo = metadata_module.MetadataRepository(session)
        playlist = repo.get_playlist_by_source_url(playlist_url)
        if playlist is None:
            playlist = repo.create_playlist(
                source_url=playlist_url,
                title=manifest_title,
                item_count=len(videos),
            )
        else:
            playlist.item_count = len(videos)
            playlist.title = manifest_title

        repo.persist_manifest(playlist, videos)
        coverage = repo.subtitle_coverage(playlist)
        return coverage


def _serialize_sequence(values: Tuple[str, ...]) -> str:
    return json.dumps(list(values))


def _deserialize_sequence(raw: str) -> Tuple[str, ...]:
    return tuple(json.loads(raw))


def _serialize_object(obj: Optional[Dict[str, Any]]) -> Optional[str]:
    if obj is None:
        return None
    return json.dumps(obj)


def _deserialize_object(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    return json.loads(raw)


def save_resume_checkpoint(database_path: Path, checkpoint: ResumeCheckpoint) -> None:
    attempts = 0
    last_error: Optional[sqlite3.OperationalError] = None

    while attempts < 3:
        try:
            _initialize_sqlite_schema(database_path)
            connection = sqlite3.connect(database_path)
            try:
                now = _utc_now_iso()
                connection.execute(
                    """
                    INSERT INTO resume_checkpoints (
                        session_id,
                        playlist_id,
                        playlist_url,
                        completed_videos,
                        pending_videos,
                        throttle_profile,
                        resumed_from,
                        manifest,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        playlist_id = excluded.playlist_id,
                        playlist_url = excluded.playlist_url,
                        completed_videos = excluded.completed_videos,
                        pending_videos = excluded.pending_videos,
                        throttle_profile = excluded.throttle_profile,
                        resumed_from = excluded.resumed_from,
                        manifest = excluded.manifest,
                        updated_at = excluded.updated_at
                    """,
                    (
                        checkpoint.session_id,
                        checkpoint.playlist_id,
                        checkpoint.playlist_url,
                        _serialize_sequence(checkpoint.completed_videos),
                        _serialize_sequence(checkpoint.pending_videos),
                        json.dumps(checkpoint.throttle_profile),
                        checkpoint.resumed_from,
                        _serialize_object(checkpoint.manifest),
                        now,
                        now,
                    ),
                )
                connection.commit()
                return
            finally:
                connection.close()
        except sqlite3.OperationalError as error:  # pragma: no cover - exercised in tests
            last_error = error
            attempts += 1
            time.sleep(min(0.1 * attempts, 0.5))

    if last_error is not None:
        raise last_error


def load_resume_checkpoint(
    database_path: Path, session_id: str
) -> Optional[ResumeCheckpoint]:
    _initialize_sqlite_schema(database_path)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            """
            SELECT session_id, playlist_id, playlist_url, completed_videos, pending_videos,
                   throttle_profile, resumed_from, manifest
            FROM resume_checkpoints
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        manifest = _deserialize_object(row["manifest"])
        if manifest is None:
            manifest = load_playlist_manifest(database_path, row["playlist_id"])
        return ResumeCheckpoint(
            session_id=row["session_id"],
            playlist_id=row["playlist_id"],
            playlist_url=row["playlist_url"],
            completed_videos=_deserialize_sequence(row["completed_videos"]),
            pending_videos=_deserialize_sequence(row["pending_videos"]),
            throttle_profile=json.loads(row["throttle_profile"]),
            resumed_from=row["resumed_from"],
            manifest=manifest,
        )
    finally:
        connection.close()


__all__ = [
    "Base",
    "PersistenceConfig",
    "configure_persistence",
    "get_engine",
    "get_session_factory",
    "session_scope",
    "metadata_session_scope",
    "record_session_run",
    "fetch_playlist_sessions",
    "ResumeCheckpoint",
    "save_resume_checkpoint",
    "load_resume_checkpoint",
    "save_playlist_manifest",
    "load_playlist_manifest",
    "persist_metadata_summary",
]
