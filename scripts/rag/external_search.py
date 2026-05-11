"""Provider-backed literature search helpers for RAG."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass

from metadata_normalizer import normalize_arxiv, normalize_doi

INSPIRE_API_BASE = "https://inspirehep.net/api/literature"


@dataclass(frozen=True)
class SearchResult:
    provider: str
    record_id: str
    title: str
    authors: list[str]
    year: str
    doi: str
    arxiv: str
    control_number: str

    @property
    def identifier(self) -> str:
        return self.doi or self.arxiv or self.control_number or self.record_id

    @property
    def pdf_url(self) -> str:
        return arxiv_pdf_url(self.arxiv)


def arxiv_pdf_url(arxiv: str) -> str:
    arxiv = normalize_arxiv(arxiv)
    if not arxiv:
        return ""
    return f"https://arxiv.org/pdf/{urllib.parse.quote(arxiv)}.pdf"


def result_summary(result: SearchResult) -> dict[str, str]:
    return {
        "provider": result.provider,
        "record_id": result.record_id,
        "title": result.title,
        "year": result.year,
        "doi": result.doi,
        "arxiv": result.arxiv,
        "pdf_url": result.pdf_url,
    }


def _fetch_text(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "rag-framework/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def _inspire_url(params: dict[str, str | int]) -> str:
    return f"{INSPIRE_API_BASE}?{urllib.parse.urlencode(params)}"


def _first_title(metadata: dict[str, object]) -> str:
    titles = metadata.get("titles", [])
    if isinstance(titles, list) and titles:
        first = titles[0]
        if isinstance(first, dict):
            return str(first.get("title", ""))
    return ""


def _authors(metadata: dict[str, object], limit: int = 5) -> list[str]:
    authors = metadata.get("authors", [])
    names: list[str] = []
    if not isinstance(authors, list):
        return names
    for author in authors[:limit]:
        if isinstance(author, dict):
            name = str(author.get("full_name") or author.get("full_name_unicode_normalized") or "").strip()
            if name:
                names.append(name)
    return names


def _year(metadata: dict[str, object]) -> str:
    imprints = metadata.get("imprints", [])
    if isinstance(imprints, list) and imprints:
        first = imprints[0]
        if isinstance(first, dict) and first.get("date"):
            return str(first["date"])[:4]
    preprint_date = metadata.get("preprint_date")
    if preprint_date:
        return str(preprint_date)[:4]
    publication_info = metadata.get("publication_info", [])
    if isinstance(publication_info, list) and publication_info:
        first = publication_info[0]
        if isinstance(first, dict) and first.get("year"):
            return str(first["year"])
    return ""


def _doi(metadata: dict[str, object]) -> str:
    dois = metadata.get("dois", [])
    if isinstance(dois, list) and dois:
        first = dois[0]
        if isinstance(first, dict):
            return normalize_doi(str(first.get("value", "")))
    return ""


def _arxiv(metadata: dict[str, object]) -> str:
    arxiv_eprints = metadata.get("arxiv_eprints", [])
    if isinstance(arxiv_eprints, list) and arxiv_eprints:
        first = arxiv_eprints[0]
        if isinstance(first, dict):
            return normalize_arxiv(str(first.get("value", "")))
    return ""


def _parse_inspire_hit(hit: dict[str, object]) -> SearchResult:
    metadata = hit.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    record_id = str(hit.get("id") or metadata.get("control_number") or "")
    control_number = str(metadata.get("control_number") or record_id)
    return SearchResult(
        provider="inspire",
        record_id=record_id,
        title=_first_title(metadata),
        authors=_authors(metadata),
        year=_year(metadata),
        doi=_doi(metadata),
        arxiv=_arxiv(metadata),
        control_number=control_number,
    )


def search_inspire(query: str, size: int = 5) -> list[SearchResult]:
    url = _inspire_url({"q": query, "size": size})
    data = json.loads(_fetch_text(url))
    hits = data.get("hits", {}).get("hits", []) if isinstance(data, dict) else []
    if not isinstance(hits, list):
        return []
    return [_parse_inspire_hit(hit) for hit in hits if isinstance(hit, dict)]


def search_inspire_by_identifier(doi: str = "", arxiv: str = "", size: int = 5) -> list[SearchResult]:
    doi = normalize_doi(doi)
    arxiv = normalize_arxiv(arxiv)
    if arxiv:
        return search_inspire(f"arxiv:{arxiv}", size=size)
    if doi:
        return search_inspire(f"doi:{doi}", size=size)
    return []


def fetch_inspire_bibtex(record_id: str) -> str:
    record_id = record_id.strip()
    if not record_id:
        return ""
    return _fetch_text(f"{INSPIRE_API_BASE}/{urllib.parse.quote(record_id)}?format=bibtex").strip()


def fetch_inspire_bibtex_for_query(query: str, size: int = 1) -> str:
    url = _inspire_url({"q": query, "size": size, "format": "bibtex"})
    return _fetch_text(url).strip()
