"""Stable, deterministic IDs (BLAKE2b hash, 16 hex chars).

We avoid stdlib's hash() because Python randomizes string hashing per-process
(PYTHONHASHSEED), which would break ID stability across runs.
"""

from __future__ import annotations

import hashlib


def stable_id(*parts: str) -> str:
    """Compute a 16-character hex hash from any number of string parts.

    Same inputs → same id, always. Different inputs → different ids with
    overwhelming probability. Order of parts matters.
    """
    joined = "\x1f".join(parts)  # ASCII unit separator (won't appear in user data)
    digest = hashlib.blake2b(joined.encode("utf-8"), digest_size=8).hexdigest()
    return digest
