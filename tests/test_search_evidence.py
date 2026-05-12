"""Tests for DARW evidence search."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from bib_parser import render_bibtex
from common import ensure_rag_dirs
from evidence_ingest import ingest_entry
from search_evidence import format_hits, search_chunks


class TestSearchEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir, ())
        entry = {
            "ENTRYTYPE": "article",
            "ID": "paper",
            "title": "Evidence Paper",
            "author": "Smith, Alice",
            "year": "2024",
            "eprint": "2401.12345",
        }
        (self.rag_dir / "references.bib").write_text(render_bibtex(entry), encoding="utf-8")
        self.parsed = self.tmp / "parsed.md"
        self.parsed.write_text(
            "# Intro\n\nSuperconducting resonators exhibit TLS noise.\n\n# Method\n\nWe measured frequency noise in NbN resonators.\n",
            encoding="utf-8",
        )
        ingest_entry(entry, self.rag_dir, arxiv_output=self.parsed)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_search_finds_relevant_chunk(self):
        hits = search_chunks(self.rag_dir, "TLS noise superconducting")
        self.assertTrue(len(hits) > 0)
        self.assertIn("TLS", hits[0].text)

    def test_search_ranks_scores_descending(self):
        hits = search_chunks(self.rag_dir, "frequency noise resonators")
        self.assertTrue(len(hits) >= 2)
        self.assertGreaterEqual(hits[0].score, hits[-1].score)

    def test_search_irrelevant_query_returns_empty(self):
        hits = search_chunks(self.rag_dir, "dark matter axion detection")
        self.assertTrue(len(hits) == 0 or all(h.score < 0.1 for h in hits))

    def test_hit_contains_provenance_fields(self):
        hits = search_chunks(self.rag_dir, "superconducting")
        self.assertTrue(len(hits) > 0)
        hit = hits[0]
        self.assertTrue(hit.chunk_id)
        self.assertTrue(hit.doc_id)
        self.assertEqual(hit.citation_key, "paper")
        self.assertIn("summary/sources/paper.md", hit.source_page)
        self.assertEqual(hit.route, "arxiv_source")

    def test_format_hits_includes_chunk_id_and_text(self):
        hits = search_chunks(self.rag_dir, "TLS noise")
        output = format_hits(hits)
        self.assertIn("chunk_id:", output)
        self.assertIn("text:", output)

    def test_format_hits_empty(self):
        self.assertEqual(format_hits([]), "No evidence chunks found.")


if __name__ == "__main__":
    unittest.main()
