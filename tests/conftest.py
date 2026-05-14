"""Pytest scratch-directory hardening for Windows/OneDrive sandboxes.

Some sandboxed Windows environments can create stdlib tempfile directories that
exist but reject subsequent writes. The test suite only needs disposable local
scratch paths, so route tempfile helpers through deterministic repo-local
directories created with pathlib.
"""

from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1] / ".tmp_pytest"


def _safe_mkdtemp(suffix: str | None = None, prefix: str | None = None, dir: str | Path | None = None) -> str:
    parent = Path(dir) if dir is not None else _ROOT
    parent.mkdir(parents=True, exist_ok=True)
    name_prefix = "tmp" if prefix is None else prefix
    name_suffix = "" if suffix is None else suffix
    for _ in range(100):
        candidate = parent / f"{name_prefix}{uuid.uuid4().hex}{name_suffix}"
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return str(candidate)
    raise FileExistsError(f"could not create unique temporary directory under {parent}")


def _safe_mktemp(suffix: str | None = None, prefix: str | None = None, dir: str | Path | None = None) -> str:
    parent = Path(dir) if dir is not None else _ROOT
    parent.mkdir(parents=True, exist_ok=True)
    name_prefix = "tmp" if prefix is None else prefix
    name_suffix = "" if suffix is None else suffix
    return str(parent / f"{name_prefix}{uuid.uuid4().hex}{name_suffix}")


class _SafeTemporaryDirectory:
    def __init__(
        self,
        suffix: str | None = None,
        prefix: str | None = None,
        dir: str | Path | None = None,
        ignore_cleanup_errors: bool = False,
        *,
        delete: bool = True,
    ) -> None:
        self.name = _safe_mkdtemp(suffix=suffix, prefix=prefix, dir=dir)
        self._delete = delete
        self._ignore_cleanup_errors = ignore_cleanup_errors

    def __enter__(self) -> str:
        return self.name

    def __exit__(self, exc_type, exc, tb) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        if self._delete:
            shutil.rmtree(self.name, ignore_errors=self._ignore_cleanup_errors)


tempfile.tempdir = str(_ROOT)
tempfile.mkdtemp = _safe_mkdtemp
tempfile.mktemp = _safe_mktemp
tempfile.TemporaryDirectory = _SafeTemporaryDirectory
