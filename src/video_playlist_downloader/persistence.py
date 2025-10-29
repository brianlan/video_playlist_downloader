"""
SQLite persistence initialization utilities.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy import exc as sa_exc
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


@dataclass(frozen=True)
class PersistenceConfig:
    """Configuration describing how to connect to the application database."""

    database_path: Path
    echo: bool = False


_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker[Session]] = None


def _build_engine(database_path: Path, echo: bool = False) -> Engine:
    database_path.parent.mkdir(parents=True, exist_ok=True)
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
    Base.metadata.create_all(engine)

    _engine = engine
    _session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Persistence not configured. Call configure_persistence() first.")
    return _engine


def get_session_factory() -> sessionmaker[Session]:
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


__all__ = [
    "Base",
    "PersistenceConfig",
    "configure_persistence",
    "get_engine",
    "get_session_factory",
    "session_scope",
]
