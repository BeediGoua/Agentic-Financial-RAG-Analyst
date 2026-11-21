from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=256)
def _sha256_cached(resolved_path: str, mtime_ns: int, size: int) -> str:
    digest = hashlib.sha256()
    with Path(resolved_path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_file(path: str | Path) -> str:
    """Return a cached SHA-256, invalidating the cache on file metadata changes."""
    source = Path(path)
    stat = source.stat()
    return _sha256_cached(str(source.resolve()), stat.st_mtime_ns, stat.st_size)
