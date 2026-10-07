"""Disk-backed LLM response cache (hash-keyed)."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import threading
from pathlib import Path

from casemap._internal.logger import get_logger

_log = get_logger("llm.cache")


class FileCache:
    """JSON-file cache with an in-memory dict for O(1) hits.

    Keys are arbitrary strings; values are arbitrary JSON-serializable data.
    Reads lazy-load the file once, then serve from memory; writes mutate the
    in-memory dict and flush through to disk via tmp+os.replace. Concurrent
    processes are guarded by fcntl.flock; concurrent threads by a Lock.
    """

    MAX_ENTRIES = 10_000  # cap to prevent unbounded growth

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}")
        # ponytail: in-process mutex. fcntl.flock has per-process semantics on
        # macOS (F_SETLK emulation) so threads in the same process don't
        # actually serialize via flock alone. This lock handles that; flock
        # handles the cross-process case (CI/CD parallel casemap runs).
        self._lock = threading.Lock()
        # ponytail: in-memory dict. None = not loaded; first get/set triggers
        # a one-time load. Subsequent operations don't touch the file on read,
        # which keeps cache hits O(1) instead of O(file_size).
        self._data: dict[str, object] | None = None

    def _load(self) -> dict[str, object]:
        """Lazy-load the on-disk cache into memory. Returns the dict (mutable
        reference; callers must hold self._lock if they'll mutate)."""
        if self._data is not None:
            return self._data
        try:
            loaded: dict[str, object] = json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            _log.warning("cache read failed (%s); starting empty", e)
            loaded = {}
        self._data = loaded
        return self._data

    def _flush(self, data: dict[str, object]) -> None:
        """Write through to disk atomically. Caller holds self._lock."""
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False))
        os.replace(tmp, self.path)

    @staticmethod
    def key_for(*parts: str) -> str:
        joined = "\x1f".join(parts)
        return hashlib.blake2b(joined.encode("utf-8"), digest_size=16).hexdigest()

    def get(self, key: str) -> object | None:
        with self._lock:
            return self._load().get(key)

    def set(self, key: str, value: object) -> None:
        # ponytail: fcntl.flock around the disk write makes concurrent writers
        # across processes serializable. The in-memory dict handles the
        # in-process case — within one process we just mutate our own dict
        # then flush; across processes flock serializes the flushes.
        with self._lock:
            data = dict(self._load())  # snapshot under lock
            data[key] = value
            # ponytail: naive FIFO eviction when over cap. Replace with LRU
            # or schema-aware eviction if cache pressure becomes real.
            if len(data) > self.MAX_ENTRIES:
                excess = len(data) - self.MAX_ENTRIES
                for k in list(data.keys())[:excess]:
                    del data[k]
            with self.path.open("r+") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    self._flush(data)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            self._data = data  # commit in-memory snapshot

    def clear(self) -> None:
        with self._lock:
            self._flush({})
            self._data = {}


__all__ = ["FileCache"]
