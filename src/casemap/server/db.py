"""SQLAlchemy engine + session factory (sync, SQLite-friendly)."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from casemap.server.config import get_settings


def _build_engine() -> Engine:
    url = get_settings().db_url
    # ponytail: SQLite needs check_same_thread=False to be reused across
    # FastAPI's threadpool; for any non-sqlite URL the connect_args would
    # be ignored and is the right thing to omit.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    # ponytail: SQLAlchemy 2.x removed `future=True` (2.0-style is the only API now).
    return create_engine(url, connect_args=connect_args)


# Module-level engine; tests swap this attribute to point at an isolated engine.
engine: Engine = _build_engine()
SessionLocal: sessionmaker[Session] = sessionmaker(bind=engine, autoflush=False)


def get_engine() -> Engine:
    return engine


def get_session_factory() -> sessionmaker[Session]:
    return SessionLocal


def reset_for_tests(new_engine: Engine | None = None) -> None:
    """Replace the cached engine + factory (tests call between scenarios)."""
    global engine, SessionLocal
    engine.dispose()
    engine = new_engine or _build_engine()
    SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a session, close it on exit."""
    factory = get_session_factory()
    sess: Session = factory()
    try:
        yield sess
    finally:
        sess.close()
