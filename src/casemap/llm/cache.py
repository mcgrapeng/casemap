"""Disk-backed LLM response cache (hash-keyed)."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from casemap._internal.logger import get_logger

_log = get_logger("llm.cache")


class FileCache:
    """Simple JSON-file cache.

    Keys are arbitrary strings; values are arbitrary JSON-serializable data.
    Safe to use across processes: writes go to a sibling .tmp file then
    os.replace, so readers never see a half-written file.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}")

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
        data = self._read()
        data[key] = value
        self._write(data)

    def clear(self) -> None:
        self._write({})
