"""Shared helpers for RAG command-line scripts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from cli_encoding import configure_utf8_stdio

configure_utf8_stdio()


def _display_path(path: Path, base_dir: Path) -> str:
    try:
        return path.resolve().relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        try:
            return Path(path).resolve().relative_to(base_dir.parent.resolve()).as_posix()
        except ValueError:
            return path.as_posix()


def ensure_rag_dirs(rag_dir: Path, dimensions: Iterable[str] = ()) -> None:
    rag_dir.mkdir(parents=True, exist_ok=True)
    (rag_dir / "summary" / "sources").mkdir(parents=True, exist_ok=True)
    (rag_dir / "summary" / "synthesis").mkdir(parents=True, exist_ok=True)
    (rag_dir / "reference" / "pdfs").mkdir(parents=True, exist_ok=True)
    (rag_dir / "reference" / "parsed").mkdir(parents=True, exist_ok=True)
    (rag_dir / "reference" / "chunks").mkdir(parents=True, exist_ok=True)
    (rag_dir / "reference" / "arxiv_sources").mkdir(parents=True, exist_ok=True)
    (rag_dir / "reference" / "imports").mkdir(parents=True, exist_ok=True)
    for dimension in dimensions:
        clean = dimension.strip()
        if clean:
            (rag_dir / "summary" / clean).mkdir(parents=True, exist_ok=True)


def append_log(rag_dir: Path, operation: str, input_value: str, result: str) -> None:
    log_path = rag_dir / "log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    base_dir = rag_dir.resolve().parent
    input_value = _relativize_paths_in_text(input_value, base_dir)
    result = _relativize_paths_in_text(result, base_dir)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"## {timestamp} | {operation}\n\n")
        handle.write(f"- input: {input_value}\n")
        handle.write(f"- result: {result}\n\n")


def _relativize_paths_in_text(text: str, base_dir: Path) -> str:
    resolved_base = base_dir.resolve()
    variants = {str(resolved_base), resolved_base.as_posix()}
    for variant in variants:
        text = text.replace(variant, ".")
    return text.replace("\\", "/")


def slugify(value: str) -> str:
    from metadata_normalizer import normalize_title

    slug = normalize_title(value).replace(" ", "-")
    return slug or "untitled"


def read_frontmatter(path: Path) -> tuple[dict[str, object], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    body = text[end + 5 :]
    frontmatter: dict[str, object] = {}
    try:
        import yaml
        parsed = yaml.safe_load(text[4:end])
        if isinstance(parsed, dict):
            return parsed, body
    except Exception:
        pass
    for raw_line in text[4:end].splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            items = [item.strip().strip('"\'') for item in value[1:-1].split(",") if item.strip()]
            frontmatter[key.strip()] = items
        else:
            frontmatter[key.strip()] = value.strip('"')
    return frontmatter, body


def write_frontmatter(data: dict[str, object]) -> str:
    import yaml

    def _none_representer(dumper, _):
        return dumper.represent_scalar("tag:yaml.org,2002:null", "null")

    yaml.add_representer(type(None), _none_representer)
    inner = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False).rstrip()
    return f"---\n{inner}\n---\n"
