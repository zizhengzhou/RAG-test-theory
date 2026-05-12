"""Tests for chunk-level evidence tracing."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from bib_parser import render_bibtex
from common import ensure_rag_dirs
from evidence_ingest import ingest_entry
from trace_claim import format_trace, trace_chunk


class TestTraceClaim(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir, ())
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
        self.parsed.write_text("# Intro\n\nRaw evidence text.\n", encoding="utf-8")
        ingest_entry(self.entry, self.rag_dir, arxiv_output=self.parsed)
        chunk_path = next((self.rag_dir / "reference" / "chunks").glob("*.jsonl"))
        import json
        self.chunk_id = json.loads(chunk_path.read_text(encoding="utf-8").splitlines()[0])["chunk_id"]

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_trace_chunk_returns_raw_text_and_paths(self):
        trace = trace_chunk(self.rag_dir, self.chunk_id)
        self.assertIsNotNone(trace)
        assert trace is not None
        self.assertEqual(trace.doc_id, "arxiv:2401.12345")
        self.assertEqual(trace.source_page, "summary/sources/paper.md")
        self.assertIn("Raw evidence text.", trace.text)
        rendered = format_trace(trace)
        self.assertIn("--- chunk text ---", rendered)
        self.assertIn("parsed_markdown: reference/parsed/arxiv_2401.12345.md", rendered)

    def test_missing_chunk_returns_none(self):
        self.assertIsNone(trace_chunk(self.rag_dir, "missing"))


if __name__ == "__main__":
    unittest.main()
