"""Download provider PDFs for RAG references."""

from __future__ import annotations

import argparse
import urllib.request
import uuid
from pathlib import Path

from external_search import arxiv_pdf_url
from pdf_validator import is_pdf


def download_pdf(url: str, out_path: Path, dry_run: bool = False, timeout: int = 60) -> bool:
    if not url:
        raise ValueError("no PDF URL available")
    if dry_run:
        print(f"[dry-run] would download {url} -> {out_path}")
        return True

    out_path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "rag-framework/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("content-type", "").lower()
        data = response.read()
    if "pdf" not in content_type and not data.startswith(b"%PDF"):
        raise ValueError(f"downloaded content is not a PDF: content-type={content_type or 'unknown'}")

    tmp_path = out_path.parent / f".{out_path.name}.{uuid.uuid4().hex[:12]}.tmp"
    tmp_path.write_bytes(data)
    try:
        if not is_pdf(tmp_path):
            raise ValueError("downloaded file failed PDF validation")
        tmp_path.replace(out_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return True


def download_arxiv_pdf(arxiv: str, out_path: Path, dry_run: bool = False, timeout: int = 60) -> bool:
    url = arxiv_pdf_url(arxiv)
    if not url:
        raise ValueError("no arXiv id available for PDF download")
    return download_pdf(url, out_path, dry_run=dry_run, timeout=timeout)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download a provider PDF")
    parser.add_argument("--arxiv", default="")
    parser.add_argument("--url", default="")
    parser.add_argument("--out", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    out_path = Path(args.out).resolve()
    try:
        if args.url:
            download_pdf(args.url, out_path, dry_run=args.dry_run)
        else:
            download_arxiv_pdf(args.arxiv, out_path, dry_run=args.dry_run)
    except ValueError as exc:
        print(str(exc))
        return 1
    print(f"downloaded: {out_path}" if not args.dry_run else "[dry-run] no files written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
