"""Auth helpers (Bearer token, project lookup)."""

from __future__ import annotations

import hashlib
import secrets

from sqlalchemy.orm import Session

from casemap.server.models import Project

_TOKEN_BYTES = 32


def generate_project_api_key() -> tuple[str, str]:
    """Generate (raw_key, sha256_hex) pair. Raw is shown ONCE."""
    raw = secrets.token_urlsafe(_TOKEN_BYTES)
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def hash_token(raw: str) -> str:
    """sha256 hex of a raw token (for lookup/compare)."""
    return hashlib.sha256(raw.encode()).hexdigest()


def find_project_by_token(db: Session, raw_token: str) -> Project | None:
    """Return Project whose stored hash matches sha256(raw_token), else None."""
    target = hash_token(raw_token)
    # ponytail: hash column is indexed implicitly via UNIQUE-like cardinality
    # for v1; raw SELECT is fine until the project count grows large enough
    # to justify a dedicated index.
    return db.query(Project).filter(Project.api_key_hash == target).one_or_none()


__all__ = ["generate_project_api_key", "hash_token", "find_project_by_token"]
