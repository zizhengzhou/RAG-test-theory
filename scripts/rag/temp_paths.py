"""Local scratch paths for RAG scripts.

The pipeline should not depend on system temp directories. On some Windows
OneDrive or sandboxed setups, stdlib tempfile directories can be created but
deny later file writes. These helpers create disposable directories under the
current workspace instead.
"""

from __future__ import annotations

import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def local_temp_dir(prefix: str = "rag_tmp_", root: Path | None = None) -> Iterator[Path]:
    scratch_root = root or (Path.cwd() / ".tmp_rag")
    scratch_root.mkdir(parents=True, exist_ok=True)
    for _ in range(100):
        candidate = scratch_root / f"{prefix}{uuid.uuid4().hex[:12]}"
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        break
    else:
        raise RuntimeError(f"could not create a unique scratch directory under {scratch_root}")

    try:
        yield candidate
    finally:
        shutil.rmtree(candidate, ignore_errors=True)

