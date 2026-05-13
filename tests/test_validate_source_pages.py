"""Tests for DARW source page validation."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from common import ensure_rag_dirs, write_frontmatter
from validate_source_pages import validate_source_pages


ALL_EDGES = {
    "research_areas": [],
    "physical_systems": [],
    "techniques": [],
    "properties": [],
    "models": [],
    "observables": [],
    "datasets": [],
    "experiments": [],
}

# At least one non-empty edge category to avoid "no edges" warning
POPULATED_EDGES = {**ALL_EDGES, "techniques": [{"canonical_id": "local:test-term", "label": "Test"}]}

BASE_FM = {
    "schema_version": "darw-source-v1",
    "doc_id": "arxiv:2401.12345",
    "citation_key": "paper",
    "identifiers": {"arxiv": "2401.12345", "doi": None, "inspire": None, "zotero_key": None, "url": None},
    "source": {
        "title": "Test", "authors": [], "year": "2024", "venue": None, "abstract": "",
        "source_type": "arxiv_source", "primary_evidence": "", "original_pdf": "",
        "original_tex": None, "source_sha256": "", "parser": "", "parser_version": "", "parsed_at": "",
    },
    "edges": dict(ALL_EDGES),
    "chunk_manifest": "",
    "quality": {"extraction_confidence": "low", "needs_human_review": True,
                "math_extraction_quality": "unknown", "metadata_conflicts": []},
    "status": {"reading_status": "unread", "relevance": "unknown", "last_checked": ""},
}


class TestValidateSourcePages(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir, ())
        self._write_vocab_skeleton()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_vocab_skeleton(self):
        (self.rag_dir / "vocabulary.md").write_text("""# DARW Vocabulary

Schema version: `darw-vocabulary-v1`

## Terms

```yaml
terms:
  - canonical_id: "local:test-term"
    label: "Test Term"
    namespace: "local"
    category: "techniques"
    aliases: []
    source: "user"
    needs_review: false
```
""", encoding="utf-8")

    def _write_source(self, key: str, fm: dict, body: str = "\n# Test\n") -> Path:
        content = write_frontmatter(fm) + body
        sp = self.rag_dir / "summary" / "sources" / f"{key}.md"
        sp.write_text(content, encoding="utf-8")
        return sp

    def _write_chunk(self, doc_id: str, records: list[dict]) -> None:
        from darw_schema import safe_doc_id
        chunks_dir = self.rag_dir / "reference" / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        path = chunks_dir / f"{safe_doc_id(doc_id)}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")

    def test_empty_dir_is_fine(self):
        (self.rag_dir / "summary" / "sources").rmdir()
        issues = validate_source_pages(self.rag_dir)
        self.assertEqual(len(issues), 0)

    def test_valid_source_page_has_no_issues(self):
        fm = dict(BASE_FM)
        fm["edges"] = dict(POPULATED_EDGES)
        self._write_source("paper", fm)
        issues = validate_source_pages(self.rag_dir)
        self.assertEqual(len(issues), 0, msg="; ".join(issues))

    def test_missing_schema_version_is_reported(self):
        fm = dict(BASE_FM)
        fm.pop("schema_version")
        self._write_source("paper", fm)
        issues = validate_source_pages(self.rag_dir)
        self.assertTrue(any("schema_version" in i for i in issues))

    def test_missing_required_block_is_reported(self):
        fm = dict(BASE_FM)
        fm.pop("quality")
        self._write_source("paper", fm)
        issues = validate_source_pages(self.rag_dir)
        self.assertTrue(any("quality" in i for i in issues))

    def test_invalid_source_type_is_reported(self):
        fm = dict(BASE_FM)
        fm["source"] = dict(BASE_FM["source"], source_type="source_page")
        self._write_source("paper", fm)
        issues = validate_source_pages(self.rag_dir)
        self.assertTrue(any("source_type" in i for i in issues))

    def test_doc_id_arxiv_inconsistency_is_reported(self):
        fm = dict(BASE_FM)
        fm["doc_id"] = "arxiv:9999.99999"
        self._write_source("paper", fm)
        issues = validate_source_pages(self.rag_dir)
        self.assertTrue(any("inconsistent" in i for i in issues))

    def test_unknown_edge_category_is_reported(self):
        fm = dict(BASE_FM)
        fm["edges"] = {"bad_category": []}
        self._write_source("paper", fm)
        issues = validate_source_pages(self.rag_dir)
        self.assertTrue(any("unknown edge category" in i for i in issues))

    def test_off_vocab_canonical_id_is_reported(self):
        (self.rag_dir / "vocabulary.md").write_text("""# DARW Vocabulary

Schema version: `darw-vocabulary-v1`

## Terms

```yaml
terms:
  - canonical_id: "local:test"
    label: "Test"
    namespace: "local"
    category: "techniques"
    aliases: []
    source: "user"
    needs_review: false
```
""", encoding="utf-8")
        fm = dict(BASE_FM)
        fm["edges"] = {**ALL_EDGES, "techniques": [{"canonical_id": "local:nonexistent", "label": "Nope"}]}
        self._write_source("paper", fm)
        issues = validate_source_pages(self.rag_dir)
        self.assertTrue(any("off-vocab" in i for i in issues))

    def test_primary_evidence_missing_is_reported(self):
        fm = dict(BASE_FM)
        fm["source"] = dict(BASE_FM["source"], primary_evidence="../../reference/parsed/nonexistent.md")
        self._write_source("paper", fm)
        issues = validate_source_pages(self.rag_dir)
        self.assertTrue(any("primary_evidence" in i for i in issues))

    def test_chunk_manifest_missing_is_reported(self):
        fm = dict(BASE_FM)
        fm["chunk_manifest"] = "../../reference/chunks/nonexistent.jsonl"
        self._write_source("paper", fm)
        issues = validate_source_pages(self.rag_dir)
        self.assertTrue(any("chunk_manifest" in i for i in issues))

    def test_claim_without_evidence_is_reported(self):
        body = "\n```claim\nclaim_id: claim-001\nstatement: \"test\"\nconfidence: \"high\"\n```\n"
        self._write_source("paper", BASE_FM, body=body)
        issues = validate_source_pages(self.rag_dir)
        self.assertTrue(any("no evidence" in i for i in issues))

    def test_claim_evidence_missing_chunk_id_is_reported(self):
        body = """\n```claim
claim_id: claim-001
statement: "test"
evidence:
  - section_anchor: "#intro"
confidence: "high"
```\n"""
        self._write_source("paper", BASE_FM, body=body)
        issues = validate_source_pages(self.rag_dir)
        self.assertTrue(any("without chunk_id" in i for i in issues))

    def test_claim_references_missing_chunk_id_is_reported(self):
        # Create a chunk manifest with a real chunk so the global ID set is non-empty
        self._write_chunk("arxiv:2401.12345", [{
            "schema_version": "darw-chunk-v1",
            "chunk_id": "real-chunk",
            "doc_id": "arxiv:2401.12345",
            "citation_key": "paper",
            "source_type": "arxiv_source",
            "parser": "arxiv2md",
            "source_sha256": "abc",
            "section_title": "Intro",
            "section_anchor": "#intro",
            "text": "Test text.",
            "contains_equation": False,
            "equation_ids": [],
            "page_start": 1,
            "page_end": 1,
            "char_start": 0,
            "char_end": 100,
            "edges": {},
            "created_at": "2024-01-01T00:00:00Z",
        }])
        body = """\n```claim
claim_id: claim-001
statement: "test"
evidence:
  - chunk_id: "nonexistent-chunk"
confidence: "high"
```\n"""
        self._write_source("paper", BASE_FM, body=body)
        issues = validate_source_pages(self.rag_dir)
        self.assertTrue(any("missing chunk_id" in i for i in issues))

    def test_claim_with_valid_chunk_id_passes(self):
        self._write_chunk("arxiv:2401.12345", [{
            "schema_version": "darw-chunk-v1",
            "chunk_id": "real-chunk",
            "doc_id": "arxiv:2401.12345",
            "citation_key": "paper",
            "source_type": "arxiv_source",
            "parser": "arxiv2md",
            "source_sha256": "abc",
            "section_title": "Intro",
            "section_anchor": "#intro",
            "text": "Test text content.",
            "contains_equation": False,
            "equation_ids": [],
            "page_start": 1,
            "page_end": 1,
            "char_start": 0,
            "char_end": 100,
            "edges": {},
            "created_at": "2024-01-01T00:00:00Z",
        }])
        body = """\n```claim
claim_id: claim-001
statement: "test"
evidence:
  - chunk_id: "real-chunk"
confidence: "high"
```\n"""
        fm = dict(BASE_FM)
        fm["edges"] = dict(POPULATED_EDGES)
        self._write_source("paper", fm, body=body)
        issues = validate_source_pages(self.rag_dir)
        self.assertEqual(len(issues), 0, msg="; ".join(issues))

    def test_strict_mode_empty_edges_are_error(self):
        fm = dict(BASE_FM)
        fm["edges"] = dict(ALL_EDGES)
        self._write_source("paper", fm)
        issues = validate_source_pages(self.rag_dir, strict=True)
        self.assertTrue(any("error" in i.lower() and "no edges" in i.lower() for i in issues))

    def test_cli_non_strict_warning_returns_zero(self):
        fm = dict(BASE_FM)
        fm["edges"] = dict(ALL_EDGES)
        self._write_source("paper", fm)

        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "rag" / "validate_source_pages.py"),
                "--rag-dir",
                str(self.rag_dir),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[warning]", result.stdout)


if __name__ == "__main__":
    unittest.main()
