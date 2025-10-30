"""
SQLite persistence initialization utilities.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional
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

from .downloader import DownloadSummary

_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS session_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        playlist_url TEXT NOT NULL,
        total INTEGER NOT NULL,
        completed INTEGER NOT NULL,
        skipped INTEGER NOT NULL,
        failed INTEGER NOT NULL,
        pending INTEGER NOT NULL,
        throttle_label TEXT NOT NULL,
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
]


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
        connection.commit()
    finally:
        connection.close()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_session_run(
    database_path: Path,
    *,
    session_id: str,
    playlist_url: str,
    summary: DownloadSummary,
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
                playlist_url,
                total,
                completed,
                skipped,
                failed,
                pending,
                throttle_label,
                elapsed_seconds,
                eta_seconds,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                playlist_url,
                summary.total,
                summary.completed,
                summary.skipped,
                summary.failed,
                summary.pending,
                summary.throttle_label,
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


__all__ = [
    "Base",
    "PersistenceConfig",
    "configure_persistence",
    "get_engine",
    "get_session_factory",
    "session_scope",
    "record_session_run",
]
