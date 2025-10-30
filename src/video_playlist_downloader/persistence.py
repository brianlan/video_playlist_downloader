"""
SQLite persistence initialization utilities.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional
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
    if engine is None:
        config.database_path.touch(exist_ok=True)
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


__all__ = [
    "Base",
    "PersistenceConfig",
    "configure_persistence",
    "get_engine",
    "get_session_factory",
    "session_scope",
]
