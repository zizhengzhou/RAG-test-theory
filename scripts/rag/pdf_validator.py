"""PDF validation for RAG imports."""

from __future__ import annotations

import argparse
from pathlib import Path


def is_pdf(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(4) == b"%PDF"
    except FileNotFoundError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PDF files")
    parser.add_argument("path")
    args = parser.parse_args()
    path = Path(args.path)
    ok = is_pdf(path)
    print("valid" if ok else "invalid")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
