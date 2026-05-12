"""Tests for parsed evidence registration."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from common import ensure_rag_dirs
from darw_schema import parsed_manifest_path, parsed_markdown_path
from parsers import EvidenceResolutionError, _load_arxiv_cache, _save_arxiv_cache, parse_evidence, register_parsed_markdown
from resolve_source import ResolvedSource


class TestParsersRouting(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir, ())
        (self.rag_dir / "reference" / "parsed").mkdir(parents=True, exist_ok=True)
        self.parsed = self.tmp / "parsed.md"
        self.parsed.write_text("# Intro\n\nEvidence text.\n", encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def resolved(self, route="arxiv_source"):
        return ResolvedSource(
            doc_id="arxiv:2301.12345" if route == "arxiv_source" else "10.1234/example",
            citation_key="paper",
            arxiv_id="2301.12345" if route == "arxiv_source" else "",
            doi="10.1234/example" if route != "arxiv_source" else "",
            title="Paper",
            pdf_path="",
            route=route,
            needs_review=False,
            metadata_conflicts=[],
        )

    def test_register_parsed_markdown_writes_manifest(self):
        evidence = register_parsed_markdown(self.resolved(), self.rag_dir, self.parsed, parser_name="arxiv2md")
        manifest = parsed_manifest_path(self.rag_dir, evidence.doc_id)
        self.assertTrue(manifest.exists())
        data = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], "darw-parsed-evidence-v1")
        self.assertEqual(data["parser"], "arxiv2md")
        self.assertTrue((self.rag_dir / data["parsed_markdown"]).exists())

    def test_parse_evidence_requires_explicit_backend_output(self):
        with self.assertRaises(EvidenceResolutionError):
            parse_evidence(self.resolved("pdf_pymupdf"), self.rag_dir)

    def test_dry_run_writes_nothing(self):
        resolved = self.resolved()
        register_parsed_markdown(resolved, self.rag_dir, self.parsed, parser_name="arxiv2md", dry_run=True)
        self.assertFalse(parsed_manifest_path(self.rag_dir, resolved.doc_id).exists())
        self.assertFalse(parsed_markdown_path(self.rag_dir, resolved.doc_id).exists())


    def test_arxiv_cache_round_trip(self):
        content = "# Cached\n\nEvidence text.\n"
        _save_arxiv_cache(self.rag_dir, "2301.12345", "test-version", content)
        self.assertEqual(_load_arxiv_cache(self.rag_dir, "2301.12345", "test-version"), content)
        self.assertIsNone(_load_arxiv_cache(self.rag_dir, "2301.12345", "other-version"))


if __name__ == "__main__":
    unittest.main()
