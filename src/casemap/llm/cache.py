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
    """Simple JSON-file cache.

    Keys are arbitrary strings; values are arbitrary JSON-serializable data.
    Safe to use across processes: writes go to a sibling .tmp file then
    os.replace, so readers never see a half-written file. The set path uses
    fcntl.flock to make the read-modify-write atomic across concurrent writers.
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

    def _read(self) -> dict[str, object]:
        try:
            result: dict[str, object] = json.loads(self.path.read_text())
            return result
        except (json.JSONDecodeError, OSError) as e:
            _log.warning("cache read failed (%s); starting empty", e)
            return {}

    def _write(self, data: dict[str, object]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False))
        os.replace(tmp, self.path)

    @staticmethod
    def key_for(*parts: str) -> str:
        joined = "\x1f".join(parts)
        return hashlib.blake2b(joined.encode("utf-8"), digest_size=16).hexdigest()

    def get(self, key: str) -> object | None:
        return self._read().get(key)

    def set(self, key: str, value: object) -> None:
        # ponytail: fcntl.flock around read+modify+write makes concurrent
        # writers serializable. Without it, two writers both read base X,
        # each appends their key, and the second write wins — silent loss.
        # The threading.Lock is the in-process piece (see __init__ comment).
        with self._lock, self.path.open("r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                try:
                    raw = f.read()
                    data: dict[str, object] = dict(json.loads(raw)) if raw else {}
                except (json.JSONDecodeError, ValueError):
                    data = {}
                data[key] = value
                # ponytail: naive FIFO eviction when over cap. Replace with
                # LRU or schema-aware eviction if cache pressure becomes real.
                if len(data) > self.MAX_ENTRIES:
                    excess = len(data) - self.MAX_ENTRIES
                    for k in list(data.keys())[:excess]:
                        del data[k]
                tmp = self.path.with_suffix(self.path.suffix + ".tmp")
                tmp.write_text(json.dumps(data, ensure_ascii=False))
                os.replace(tmp, self.path)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def clear(self) -> None:
        with self._lock:
            self._write({})
