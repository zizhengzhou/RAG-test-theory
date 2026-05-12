"""Tests for evidence_ingest integration."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from bib_parser import render_bibtex
from common import ensure_rag_dirs, read_frontmatter
from darw_schema import chunk_manifest_path, parsed_manifest_path
from evidence_ingest import ingest_entry
from source_page_builder import default_frontmatter, body_skeleton


class TestEvidenceIngest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir, ())
        (self.rag_dir / "reference" / "parsed").mkdir(parents=True, exist_ok=True)
        (self.rag_dir / "reference" / "chunks").mkdir(parents=True, exist_ok=True)
        self.entry = {
            "ENTRYTYPE": "article",
            "ID": "paper",
            "title": "Evidence Paper",
            "author": "Smith, Alice",
            "year": "2024",
            "eprint": "2401.12345",
        }
        (self.rag_dir / "references.bib").write_text(render_bibtex(self.entry), encoding="utf-8")
        self.parsed = self.tmp / "parsed.md"
        self.parsed.write_text("# Intro\n\nRaw evidence.\n", encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_evidence_ingest_updates_source_frontmatter(self):
        self.assertTrue(ingest_entry(self.entry, self.rag_dir, arxiv_output=self.parsed))
        manifest = parsed_manifest_path(self.rag_dir, "arxiv:2401.12345")
        chunks = chunk_manifest_path(self.rag_dir, "arxiv:2401.12345")
        self.assertTrue(manifest.exists())
        self.assertTrue(chunks.exists())
        source = self.rag_dir / "summary" / "sources" / "paper.md"
        fm, body = read_frontmatter(source)
        self.assertEqual(fm["doc_id"], "arxiv:2401.12345")
        self.assertEqual(fm["source"]["primary_evidence"], "reference/parsed/arxiv_2401.12345.md")
        self.assertEqual(fm["chunk_manifest"], "reference/chunks/arxiv_2401.12345.jsonl")
        self.assertIn("# Evidence Paper", body)

    def test_evidence_ingest_preserves_existing_body(self):
        source = self.rag_dir / "summary" / "sources" / "paper.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        fm = default_frontmatter(self.entry, self.rag_dir)
        source.write_text("---\n" + "schema_version: darw-source-v1\n" + "---\n\nManual body.\n", encoding="utf-8")
        self.assertTrue(ingest_entry(self.entry, self.rag_dir, arxiv_output=self.parsed))
        self.assertIn("Manual body.", source.read_text(encoding="utf-8"))

    def test_dry_run_writes_nothing(self):
        self.assertTrue(ingest_entry(self.entry, self.rag_dir, arxiv_output=self.parsed, dry_run=True))
        self.assertFalse(parsed_manifest_path(self.rag_dir, "arxiv:2401.12345").exists())
        self.assertFalse((self.rag_dir / "summary" / "sources" / "paper.md").exists())


if __name__ == "__main__":
    unittest.main()
