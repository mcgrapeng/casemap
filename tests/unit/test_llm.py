"""Tests for the LLM abstraction layer (config / provider protocol / disk cache)."""

from __future__ import annotations

from pathlib import Path

import pytest

from casemap.llm.cache import FileCache
from casemap.llm.config import LLMConfig
from casemap.llm.provider import LLMProvider


class TestLLMConfig:
    def test_minimal(self):
        c = LLMConfig(provider="openai", model="gpt-4o-mini", api_key="sk-test")
        assert c.base_url is None
        assert c.timeout == 30.0
        assert c.max_retries == 3

    def test_env_var_fallback(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
        c = LLMConfig(provider="openai", model="gpt-4o-mini")
        assert c.api_key == "sk-env"

    def test_strict_single_model(self):
        # Per spec #11: must reject multi-model lists
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            LLMConfig(provider="openai", model=["a", "b"], api_key="sk")  # type: ignore[arg-type]


class TestFileCache:
    def test_get_set(self, tmp_path: Path):
        cache = FileCache(tmp_path / "cache.json")
        cache.set("k1", "value1")
        assert cache.get("k1") == "value1"
        assert cache.get("missing") is None

    def test_persists(self, tmp_path: Path):
        path = tmp_path / "cache.json"
        c1 = FileCache(path)
        c1.set("k", "v")
        c2 = FileCache(path)
        assert c2.get("k") == "v"

    def test_corrupt_file_returns_empty(self, tmp_path: Path):
        path = tmp_path / "cache.json"
        path.write_text("not json{")
        c = FileCache(path)
        assert c.get("k") is None  # no crash

    # ---------- SP-5 Important #2 + #5: race-free concurrent writes + size cap --

    def test_concurrent_writes_preserve_all_entries(self, tmp_path: Path):
        """With a file lock, N threads writing distinct keys must see all N.

        Without locking (the prior code), the read-modify-write race loses
        entries: two writers both read base X, each appends their own key,
        the second write wins. We assert all 50 keys survive.
        """
        import threading

        from casemap.llm.cache import FileCache

        path = tmp_path / "race.json"
        cache = FileCache(path)

        n_threads = 50
        errors: list[BaseException] = []

        def worker(i: int) -> None:
            try:
                cache.set(f"k{i}", f"v{i}")
            except BaseException as e:  # pragma: no cover - bubble up
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors, errors

        import json as _json

        on_disk = dict(_json.loads(path.read_text()))
        # Every key must be present (no read-modify-write loss)
        for i in range(n_threads):
            assert f"k{i}" in on_disk, f"key k{i} lost in race"
            assert on_disk[f"k{i}"] == f"v{i}"

    def test_bounded_by_max_entries(self, tmp_path: Path):
        """Cache must cap at MAX_ENTRIES; oldest entries get evicted FIFO."""
        from casemap.llm.cache import FileCache

        path = tmp_path / "bounded.json"
        cache = FileCache(path)
        # Write more than MAX_ENTRIES
        for i in range(FileCache.MAX_ENTRIES + 50):
            cache.set(f"k{i}", i)

        import json as _json

        on_disk = dict(_json.loads(path.read_text()))
        assert len(on_disk) <= FileCache.MAX_ENTRIES, (
            f"cache grew to {len(on_disk)} entries, cap is {FileCache.MAX_ENTRIES}"
        )


class FakeProvider:
    """For testing things that consume an LLMProvider."""

    name = "fake"
    last_prompt: str | None = None

    def __init__(self, response: str = "ok"):
        self._response = response

    async def complete(self, prompt, *, system=None):
        self.last_prompt = prompt
        return self._response

    async def complete_json(self, prompt, *, schema, system=None):
        # Wrap response in a JSON object (simple)
        return schema.model_validate({"value": self._response})


def test_provider_protocol_satisfied():
    p = FakeProvider()
    assert isinstance(p, LLMProvider)
