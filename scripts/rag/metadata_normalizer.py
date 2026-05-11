"""Normalization helpers for RAG metadata."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
ARXIV_RE = re.compile(r"(?:arXiv:)?(?P<id>\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+\/\d{7}(?:v\d+)?)", re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[^\w\s]+", re.UNICODE)


def normalize_doi(value: str | None) -> str:
    if not value:
        return ""
    match = DOI_RE.search(value)
    return match.group(0).lower().rstrip(".") if match else value.strip().lower()


def normalize_arxiv(value: str | None) -> str:
    if not value:
        return ""
    match = ARXIV_RE.search(value)
    if not match:
        return value.strip().lower()
    return match.group("id").lower()


def normalize_title(value: str | None) -> str:
    if not value:
        return ""
    text = value.lower().strip()
    text = PUNCT_RE.sub(" ", text)
    text = SPACE_RE.sub(" ", text)
    return text.strip()


def normalize_authors(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        authors = value
    else:
        authors = re.split(r"\s+and\s+", value, flags=re.IGNORECASE)
    cleaned: list[str] = []
    for author in authors:
        text = SPACE_RE.sub(" ", author.replace("{", "").replace("}", "").strip())
        if text:
            cleaned.append(text)
    return cleaned


DATACITE_ARXIV_RE = re.compile(r"10\.\d{4,}/[Aa]r[Xx]iv[./-](\d{4}\.\d{4,5}(?:v\d+)?)")


def _is_datacite_arxiv(doi: str) -> bool:
    return bool(DATACITE_ARXIV_RE.search(doi))


def normalize_entry(entry: dict[str, str]) -> dict[str, object]:
    title = entry.get("title", "")
    authors = normalize_authors(entry.get("author"))
    doi = normalize_doi(entry.get("doi"))
    arxiv = normalize_arxiv(entry.get("eprint") or entry.get("arxiv"))
    # If the DOI is a DataCite arXiv DOI (e.g. 10.48550/arXiv.2603.24450),
    # extract the true arXiv ID and clear the DOI so dedup works across entries
    # that use different identifier formats.
    if doi and _is_datacite_arxiv(doi):
        match = DATACITE_ARXIV_RE.search(doi)
        if match and not arxiv:
            arxiv = match.group(1).lower()
        doi = ""
    year = entry.get("year", "").strip()
    key = entry.get("ID", "").strip()
    return {
        "key": key,
        "title": title.strip(),
        "title_norm": normalize_title(title),
        "authors": authors,
        "doi": doi,
        "arxiv": arxiv,
        "year": year,
    }


def best_identifier(entry: dict[str, str]) -> str:
    normalized = normalize_entry(entry)
    if normalized["doi"]:
        return str(normalized["doi"])
    if normalized["arxiv"]:
        return str(normalized["arxiv"])
    if normalized["title_norm"]:
        return str(normalized["title_norm"])
    return str(normalized["key"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize RAG metadata")
    parser.add_argument("--title", default="")
    parser.add_argument("--doi", default="")
    parser.add_argument("--arxiv", default="")
    args = parser.parse_args()
    print(f"title={normalize_title(args.title)}")
    print(f"doi={normalize_doi(args.doi)}")
    print(f"arxiv={normalize_arxiv(args.arxiv)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
