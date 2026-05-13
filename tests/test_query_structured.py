"""Tests for structured Markdown/BibTeX query fallback."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from bib_parser import render_bibtex
from common import ensure_rag_dirs
from query import structured_search


class TestQueryStructured(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir)
        entry = {
            "ENTRYTYPE": "article",
            "ID": "chen2024improved",
            "title": "Improved Coupled-Channel Analysis of Breakup Reactions",
            "author": "Chen, Wei",
            "year": "2024",
            "doi": "10.5678/prc.2024.024612",
            "eprint": "2401.00001",
        }
        (self.rag_dir / "references.bib").write_text(render_bibtex(entry), encoding="utf-8")
        (self.rag_dir / "summary" / "sources" / "chen2024improved.md").write_text(
            "---\nschema_version: darw-source-v1\ncitation_key: chen2024improved\n---\n\nBreakup reaction analysis.\n",
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_key_exact_match(self):
        results = structured_search(self.rag_dir, "chen2024improved")

        self.assertEqual(results[0]["citation_key"], "chen2024improved")
        self.assertIn("citation_key", results[0]["matched_fields"])

    def test_title_keyword_match(self):
        results = structured_search(self.rag_dir, "Coupled-Channel")

        self.assertEqual(results[0]["citation_key"], "chen2024improved")
        self.assertIn("title-substring", results[0]["matched_fields"])

    def test_doi_and_arxiv_match(self):
        doi_results = structured_search(self.rag_dir, "10.5678/prc.2024.024612")
        arxiv_results = structured_search(self.rag_dir, "2401.00001")

        self.assertIn("doi", doi_results[0]["matched_fields"])
        self.assertIn("arxiv", arxiv_results[0]["matched_fields"])


if __name__ == "__main__":
    unittest.main()
