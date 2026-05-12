"""Tests for DARW evidence validation."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from bib_parser import render_bibtex
from common import ensure_rag_dirs
from evidence_ingest import ingest_entry
from validate_evidence import validate_evidence


class TestValidateEvidence(unittest.TestCase):
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
        self.parsed.write_text("# Intro\n\nRaw evidence.\n\n$$x=1$$\n", encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_valid_generated_evidence_has_no_issues(self):
        self.assertTrue(ingest_entry(self.entry, self.rag_dir, arxiv_output=self.parsed))
        self.assertEqual(validate_evidence(self.rag_dir), [])

    def test_invalid_chunk_schema_is_reported(self):
        self.assertTrue(ingest_entry(self.entry, self.rag_dir, arxiv_output=self.parsed))
        chunk_path = next((self.rag_dir / "reference" / "chunks").glob("*.jsonl"))
        text = chunk_path.read_text(encoding="utf-8").replace("darw-chunk-v1", "bad-schema", 1)
        chunk_path.write_text(text, encoding="utf-8")
        issues = validate_evidence(self.rag_dir)
        self.assertTrue(any("wrong chunk schema" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
