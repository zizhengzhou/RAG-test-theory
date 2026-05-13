"""Tests for hybrid query fallback."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from bib_parser import render_bibtex
from common import ensure_rag_dirs
from evidence_ingest import ingest_entry
from query_hybrid import query_hybrid


class TestQueryHybrid(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir)
        entry = {
            "ENTRYTYPE": "article",
            "ID": "paper",
            "title": "Evidence Paper",
            "author": "Smith, Alice",
            "year": "2024",
            "eprint": "2401.12345",
        }
        (self.rag_dir / "references.bib").write_text(render_bibtex(entry), encoding="utf-8")
        parsed = self.tmp / "parsed.md"
        parsed.write_text("# Intro\n\nSuperconducting resonators exhibit TLS noise.\n", encoding="utf-8")
        ingest_entry(entry, self.rag_dir, arxiv_output=parsed)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_query_hybrid_returns_chunk_candidates(self):
        result = query_hybrid(self.rag_dir, "TLS noise")

        self.assertEqual(result["retrieval"]["mode"], "tfidf-fallback")
        self.assertTrue(result["answer_candidates"])
        self.assertTrue(result["answer_candidates"][0]["chunk_id"])


if __name__ == "__main__":
    unittest.main()
