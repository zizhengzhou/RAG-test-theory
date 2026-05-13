"""Tests for structured context packs."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from bib_parser import render_bibtex
from common import ensure_rag_dirs
from context_pack import build_context_pack
from evidence_ingest import ingest_entry
from source_page_builder import body_skeleton, default_frontmatter, format_frontmatter


class TestContextPack(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir)
        self.evidence_entry = {
            "ENTRYTYPE": "article",
            "ID": "paper",
            "title": "Evidence Paper",
            "author": "Smith, Alice",
            "year": "2024",
            "eprint": "2401.12345",
        }
        self.metadata_entry = {
            "ENTRYTYPE": "article",
            "ID": "meta",
            "title": "Metadata Only Paper",
            "author": "Jones, Bob",
            "year": "2025",
            "doi": "10.1000/meta",
        }
        (self.rag_dir / "references.bib").write_text(
            render_bibtex(self.evidence_entry) + "\n\n" + render_bibtex(self.metadata_entry),
            encoding="utf-8",
        )
        parsed = self.tmp / "parsed.md"
        parsed.write_text(
            "# Intro\n\nSuperconducting resonators exhibit TLS noise.\n\n# Method\n\nFrequency noise was measured.\n",
            encoding="utf-8",
        )
        ingest_entry(self.evidence_entry, self.rag_dir, arxiv_output=parsed)
        meta_source = self.rag_dir / "summary" / "sources" / "meta.md"
        meta_source.write_text(
            format_frontmatter(default_frontmatter(self.metadata_entry, self.rag_dir))
            + body_skeleton(self.metadata_entry, self.rag_dir),
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_query_pack_contains_chunks_source_and_bibtex(self):
        pack = build_context_pack(self.rag_dir, query="TLS noise superconducting", top_k=3)

        self.assertEqual(pack["query"], "TLS noise superconducting")
        self.assertTrue(pack["evidence_chunks"])
        self.assertEqual(pack["evidence_chunks"][0]["citation_key"], "paper")
        self.assertTrue(pack["source_pages"])
        self.assertIn("@article{paper", pack["bib_entries"][0]["bibtex"])

    def test_key_pack_metadata_only_reports_gap(self):
        pack = build_context_pack(self.rag_dir, key="meta")

        self.assertEqual(pack["key"], "meta")
        self.assertEqual(pack["evidence_chunks"], [])
        self.assertTrue(pack["source_pages"])
        self.assertTrue(any("metadata_only" in gap for gap in pack["gaps"]))
        self.assertIn("@article{meta", pack["bib_entries"][0]["bibtex"])


if __name__ == "__main__":
    unittest.main()
