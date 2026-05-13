"""Tests for topic summary drafts."""

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
from summarize_topic import build_topic_summary, render_summary


class TestSummarizeTopic(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir)
        entry = {"ENTRYTYPE": "article", "ID": "paper", "title": "Evidence Paper", "author": "A", "year": "2024", "eprint": "2401.12345"}
        (self.rag_dir / "references.bib").write_text(render_bibtex(entry), encoding="utf-8")
        parsed = self.tmp / "parsed.md"
        parsed.write_text("# Intro\n\nSuperconducting resonators exhibit TLS noise.\n", encoding="utf-8")
        ingest_entry(entry, self.rag_dir, arxiv_output=parsed)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_summary_contains_chunk_provenance(self):
        summary = build_topic_summary(self.rag_dir, "TLS noise")
        rendered = render_summary(summary)

        self.assertTrue(summary["consensus"])
        self.assertIn("chunk", rendered.lower())
        self.assertIn("paper", rendered)


if __name__ == "__main__":
    unittest.main()
