"""Search RAG literature records and export canonical BibTeX/reading lists."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from bib_parser import parse_bibtex_file, render_bibtex
from common import read_frontmatter
from external_search import SearchResult, fetch_inspire_bibtex, search_inspire, search_inspire_by_identifier
from metadata_normalizer import normalize_arxiv, normalize_doi, normalize_entry, normalize_title


@dataclass(frozen=True)
class LocalCandidate:
    entry: dict[str, str]
    score: int
    reasons: list[str]
    source_path: Path | None
    source_fm: dict[str, object]

    @property
    def key(self) -> str:
        return self.entry.get("ID", "")

    @property
    def title(self) -> str:
        return self.entry.get("title", "")

    @property
    def year(self) -> str:
        return self.entry.get("year", "")

    @property
    def doi(self) -> str:
        return normalize_doi(self.entry.get("doi"))

    @property
    def arxiv(self) -> str:
        return normalize_arxiv(self.entry.get("eprint") or self.entry.get("arxiv"))


def _entries(rag_dir: Path) -> list[dict[str, str]]:
    manifest = rag_dir / "references.bib"
    if not manifest.exists():
        return []
    return parse_bibtex_file(manifest)


def _source_info(rag_dir: Path, key: str) -> tuple[Path | None, dict[str, object], str]:
    source = rag_dir / "summary" / "sources" / f"{key}.md"
    if not source.exists():
        return None, {}, ""
    fm, body = read_frontmatter(source)
    return source, fm, body


def _pdf_exists(rag_dir: Path, key: str) -> bool:
    return (rag_dir / "reference" / "pdfs" / f"{key}.pdf").exists()


def _queries(args: argparse.Namespace) -> list[str]:
    values: list[str] = []
    for query in getattr(args, "query", []) or []:
        text = query.strip()
        if text:
            values.append(text)
    return values


def _score_entry(entry: dict[str, str], query: str, source_text: str) -> tuple[int, list[str]]:
    normalized = normalize_entry(entry)
    q = query.strip()
    q_norm = normalize_title(q)
    q_doi = normalize_doi(q)
    q_arxiv = normalize_arxiv(q)
    score = 0
    reasons: list[str] = []

    key = str(normalized["key"])
    title = str(normalized["title"])
    title_norm = str(normalized["title_norm"])
    doi = str(normalized["doi"])
    arxiv = str(normalized["arxiv"])
    authors = " ".join(str(a) for a in normalized["authors"])
    haystack = normalize_title(" ".join([key, title, authors, source_text]))

    if q.lower() == key.lower():
        score += 100
        reasons.append("key")
    if q_doi and doi and q_doi == doi:
        score += 95
        reasons.append("doi")
    if q_arxiv and arxiv and q_arxiv == arxiv:
        score += 95
        reasons.append("arxiv")
    if q_norm and title_norm and q_norm == title_norm:
        score += 90
        reasons.append("title")
    elif q_norm and title_norm and (q_norm in title_norm or title_norm in q_norm):
        score += 50
        reasons.append("title-substring")
    if q_norm and q_norm in haystack:
        score += 25
        reasons.append("text")
    tokens = [token for token in q_norm.split() if len(token) > 2]
    if tokens:
        matched = sum(1 for token in tokens if token in haystack)
        if matched:
            score += matched * 4
            reasons.append("tokens")
    return score, reasons


def local_search(rag_dir: Path, queries: list[str], keys: list[str] | None = None, tags: list[str] | None = None, limit: int = 10) -> list[LocalCandidate]:
    entries = _entries(rag_dir)
    key_filter = {key.lower() for key in keys or []}
    tag_filters = _parse_tags(tags or [])
    candidates: list[LocalCandidate] = []
    for entry in entries:
        key = entry.get("ID", "")
        source_path, fm, body = _source_info(rag_dir, key)
        if key_filter and key.lower() not in key_filter:
            continue
        if tag_filters and not _matches_tags(fm, tag_filters):
            continue
        if key_filter or tag_filters:
            score = 100 if key_filter else 60
            reasons = ["key" if key_filter else "tag"]
        else:
            scores = [_score_entry(entry, query, body) for query in queries]
            score = max((item[0] for item in scores), default=0)
            reasons = [reason for item in scores if item[0] == score for reason in item[1]]
            if score <= 0:
                continue
        candidates.append(LocalCandidate(entry, score, sorted(set(reasons)), source_path, fm))
    candidates.sort(key=lambda item: (-item.score, item.key.lower()))
    return candidates[:limit]


def _parse_tags(tags: list[str]) -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    for tag in tags:
        if "=" not in tag:
            raise ValueError(f"invalid tag filter, expected axis=value: {tag}")
        axis, value = tag.split("=", 1)
        parsed.append((axis.strip(), value.strip()))
    return parsed


def _matches_tags(fm: dict[str, object], tags: list[tuple[str, str]]) -> bool:
    for axis, expected in tags:
        value = fm.get(axis, [])
        if not isinstance(value, list) or expected not in [str(item).strip() for item in value]:
            return False
    return True


def _inspire_query_for_candidate(candidate: LocalCandidate) -> str:
    if candidate.arxiv:
        return f"arxiv:{candidate.arxiv}"
    if candidate.doi:
        return f"doi:{candidate.doi}"
    return candidate.title


def _inspire_results_for_candidate(candidate: LocalCandidate, limit: int) -> list[SearchResult]:
    if candidate.arxiv or candidate.doi:
        results = search_inspire_by_identifier(candidate.doi, candidate.arxiv, size=limit)
        if results:
            return results
    return search_inspire(candidate.title, size=limit)


def _format_inspire_result(result: SearchResult, index: int) -> str:
    authors = ", ".join(result.authors[:3])
    suffix = " et al." if len(result.authors) > 3 else ""
    bits = [f"[{index}] INSPIRE:{result.record_id}", result.title]
    if result.year:
        bits.append(f"({result.year})")
    if authors:
        bits.append(f"by {authors}{suffix}")
    if result.arxiv:
        bits.append(f"arXiv:{result.arxiv}")
    if result.doi:
        bits.append(f"doi:{result.doi}")
    return " ".join(bits)


def command_search(args: argparse.Namespace) -> int:
    rag_dir = Path(args.rag_dir).resolve()
    queries = _queries(args)
    if not queries and not args.key and not args.tag:
        print("provide --query, --key, or --tag")
        return 1
    local = local_search(rag_dir, queries, args.key, args.tag, args.limit)
    if local:
        print("# Local RAG candidates")
        for i, candidate in enumerate(local, 1):
            pdf = "pdf" if _pdf_exists(rag_dir, candidate.key) else "no-pdf"
            print(f"[{i}] {candidate.key} score={candidate.score} {pdf} {candidate.title} ({candidate.year}) reasons={','.join(candidate.reasons)}")
    else:
        print("# Local RAG candidates\nnone")

    if args.provider == "inspire":
        print("\n# INSPIRE candidates")
        inspire_seen: set[str] = set()
        if local:
            for candidate in local[: args.limit]:
                for result in _inspire_results_for_candidate(candidate, args.limit):
                    if result.record_id in inspire_seen:
                        continue
                    inspire_seen.add(result.record_id)
                    print(_format_inspire_result(result, len(inspire_seen)))
        else:
            for query in queries:
                for result in search_inspire(query, size=args.limit):
                    if result.record_id in inspire_seen:
                        continue
                    inspire_seen.add(result.record_id)
                    print(_format_inspire_result(result, len(inspire_seen)))
        if not inspire_seen:
            print("none")
    return 0


def _bibtex_for_candidate(candidate: LocalCandidate, provider: str, fallback_local: bool) -> str:
    if provider == "inspire":
        query = _inspire_query_for_candidate(candidate)
        results = _inspire_results_for_candidate(candidate, 1)
        if results:
            bibtex = fetch_inspire_bibtex(results[0].record_id)
            if bibtex:
                return bibtex
        if not fallback_local:
            raise RuntimeError(f"INSPIRE BibTeX not found for {candidate.key} ({query})")
    return render_bibtex(candidate.entry)


def _write_or_print(text: str, out: str) -> None:
    if out:
        path = Path(out).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote: {path}")
    else:
        print(text)


def _selected_candidates(args: argparse.Namespace) -> list[LocalCandidate]:
    rag_dir = Path(args.rag_dir).resolve()
    queries = _queries(args)
    candidates = local_search(rag_dir, queries, args.key, args.tag, args.limit)
    if not candidates and queries and args.provider == "inspire":
        return []
    return candidates


def command_get_bibtex(args: argparse.Namespace) -> int:
    rag_dir = Path(args.rag_dir).resolve()
    queries = _queries(args)
    candidates = local_search(rag_dir, queries, args.key, args.tag, args.limit)
    if candidates:
        if args.format == "candidates":
            for i, candidate in enumerate(candidates, 1):
                print(f"[{i}] {candidate.key} score={candidate.score} {candidate.title} ({candidate.year})")
            return 0
        text = _bibtex_for_candidate(candidates[0], args.provider, args.fallback_local)
        print(text)
        return 0
    if args.provider == "inspire" and queries:
        bibtex_blocks: list[str] = []
        for query in queries[: args.limit]:
            results = search_inspire(query, size=1)
            if results:
                bibtex_blocks.append(fetch_inspire_bibtex(results[0].record_id))
        if bibtex_blocks:
            print("\n\n".join(block for block in bibtex_blocks if block))
            return 0
    print("no matching BibTeX found")
    return 1


def command_export_bibtex(args: argparse.Namespace) -> int:
    candidates = _selected_candidates(args)
    if not candidates:
        print("no matching entries to export")
        return 1
    blocks = [_bibtex_for_candidate(candidate, args.provider, args.fallback_local) for candidate in candidates]
    _write_or_print("\n\n".join(blocks).strip() + "\n", args.out)
    return 0


def _summary_status(source_path: Path | None) -> str:
    if not source_path or not source_path.exists():
        return "no source page"
    text = source_path.read_text(encoding="utf-8")
    if "_No summary yet._" in text or "_To be filled._" in text:
        return "placeholder"
    return "summarized"


def command_export_reading_list(args: argparse.Namespace) -> int:
    rag_dir = Path(args.rag_dir).resolve()
    candidates = _selected_candidates(args)
    if not candidates:
        print("no matching entries to export")
        return 1
    lines = ["# Reading List", ""]
    for candidate in candidates:
        source_rel = candidate.source_path.relative_to(rag_dir).as_posix() if candidate.source_path else ""
        pdf_rel = f"reference/pdfs/{candidate.key}.pdf" if _pdf_exists(rag_dir, candidate.key) else ""
        lines.append(f"- **{candidate.title}** ({candidate.year})")
        lines.append(f"  - Key: `{candidate.key}`")
        if candidate.arxiv:
            lines.append(f"  - arXiv: {candidate.arxiv}")
        if candidate.doi:
            lines.append(f"  - DOI: {candidate.doi}")
        if source_rel:
            lines.append(f"  - Source: [{candidate.key}]({source_rel})")
        if pdf_rel:
            lines.append(f"  - PDF: [{candidate.key}.pdf]({pdf_rel})")
        lines.append(f"  - Summary status: {_summary_status(candidate.source_path)}")
    _write_or_print("\n".join(lines) + "\n", args.out)
    return 0


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--key", action="append", default=[])
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--provider", choices=["inspire", "local"], default="inspire")
    parser.add_argument("--limit", type=int, default=5)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Search and export RAG literature records")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search")
    _add_common(search_parser)
    search_parser.set_defaults(func=command_search)

    get_parser = subparsers.add_parser("get-bibtex")
    _add_common(get_parser)
    get_parser.add_argument("--fallback-local", action="store_true")
    get_parser.add_argument("--format", choices=["bibtex", "candidates"], default="bibtex")
    get_parser.set_defaults(func=command_get_bibtex)

    bib_parser = subparsers.add_parser("export-bibtex")
    _add_common(bib_parser)
    bib_parser.add_argument("--fallback-local", action="store_true")
    bib_parser.add_argument("--out", default="")
    bib_parser.set_defaults(func=command_export_bibtex)

    reading_parser = subparsers.add_parser("export-reading-list")
    _add_common(reading_parser)
    reading_parser.add_argument("--out", default="")
    reading_parser.set_defaults(func=command_export_reading_list)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except ValueError as exc:
        print(str(exc))
        return 1
    except RuntimeError as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
