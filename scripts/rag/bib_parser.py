"""BibTeX parsing helpers for RAG."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ENTRY_RE = re.compile(r"@(?P<type>\w+)\s*\{", re.IGNORECASE)


def _extract_entries(text: str) -> list[str]:
    entries: list[str] = []
    i = 0
    while True:
        match = ENTRY_RE.search(text, i)
        if not match:
            break
        start = match.start()
        brace_start = text.find("{", match.end() - 1)
        depth = 0
        in_quote = False
        escape = False
        for pos in range(brace_start, len(text)):
            ch = text[pos]
            if in_quote:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_quote = False
                continue
            if ch == '"':
                in_quote = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    entries.append(text[start : pos + 1])
                    i = pos + 1
                    break
        else:
            break
    return entries


def _split_key_value(line: str) -> tuple[str, str] | None:
    if "=" not in line:
        return None
    key, value = line.split("=", 1)
    return key.strip().lower(), value.strip().rstrip(",")


def _strip_wrapping(value: str) -> str:
    value = value.strip()
    if value.startswith("{") and value.endswith("}"):
        return value[1:-1].strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1].strip()
    return value


def parse_bibtex(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for entry_text in _extract_entries(text):
        header_end = entry_text.find("{")
        entry_type = entry_text[1:header_end].strip().lower()
        rest = entry_text[header_end + 1 :].rsplit("}", 1)[0]
        if "," not in rest:
            continue
        key, body = rest.split(",", 1)
        fields: dict[str, str] = {"ENTRYTYPE": entry_type, "ID": key.strip()}
        current_key = None
        current_value_parts: list[str] = []
        for raw_line in body.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if current_key is None:
                parsed = _split_key_value(line)
                if parsed is None:
                    continue
                current_key, value = parsed
                current_value_parts = [value]
                if value.count("{") == value.count("}") and value.count('"') in (0, 2):
                    fields[current_key] = _strip_wrapping(" ".join(current_value_parts).rstrip(","))
                    current_key = None
                    current_value_parts = []
            else:
                current_value_parts.append(line)
                joined = " ".join(current_value_parts)
                if joined.count("{") == joined.count("}") and joined.count('"') in (0, 2):
                    fields[current_key] = _strip_wrapping(joined.rstrip(","))
                    current_key = None
                    current_value_parts = []
        entries.append(fields)
    return entries


def parse_bibtex_file(path: Path) -> list[dict[str, str]]:
    return parse_bibtex(path.read_text(encoding="utf-8"))


def render_bibtex(entry: dict[str, str]) -> str:
    entrytype = entry.get("ENTRYTYPE", "article")
    key = entry.get("ID", "unknown")
    lines = [f"@{entrytype}{{{key},"]
    for field, value in entry.items():
        if field in {"ENTRYTYPE", "ID"}:
            continue
        lines.append(f"  {field} = {{{value}}},")
    lines.append("}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse BibTeX entries")
    parser.add_argument("--bib", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    entries = parse_bibtex_file(Path(args.bib))
    if args.json:
        print(json.dumps(entries, indent=2, ensure_ascii=False))
    else:
        for entry in entries:
            print(render_bibtex(entry))
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
