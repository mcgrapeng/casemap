"""Auth + project lookup tests."""

from __future__ import annotations

from casemap.server.auth import (
    find_project_by_token,
    generate_project_api_key,
    hash_token,
)
from casemap.server.models import Project


def test_generate_project_api_key_returns_raw_and_hash():
    raw, hashed = generate_project_api_key()
    assert isinstance(raw, str) and len(raw) >= 32
    assert len(hashed) == 64  # sha256 hex
    assert hash_token(raw) == hashed


def test_generate_keys_differ_each_call():
    a, _ = generate_project_api_key()
    b, _ = generate_project_api_key()
    assert a != b


def test_find_project_by_token_roundtrip(db_session):
    raw, _ = generate_project_api_key()
    project = Project(id="p-1", name="p", api_key_hash=hash_token(raw))
    db_session.add(project)
    db_session.commit()

    found = find_project_by_token(db_session, raw)
    assert found is not None
    assert found.id == "p-1"


def test_find_project_by_token_wrong_key_returns_none(db_session):
    raw, _ = generate_project_api_key()
    project = Project(id="p-2", name="p", api_key_hash=hash_token(raw))
    db_session.add(project)
    db_session.commit()
    assert find_project_by_token(db_session, "not-the-key") is None


def test_find_project_by_token_db_empty_returns_none(db_session):
    assert find_project_by_token(db_session, "anything") is None
