"""Tests for one-command RAG bootstrap."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from bib_parser import parse_bibtex_file
from bootstrap_rag import bootstrap


class TestBootstrapRag(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        self.pdf = self.tmp / "paper2026.pdf"
        self.pdf.write_bytes(b"%PDF-1.4\n%%EOF")
        self.bib = self.tmp / "refs.bib"
        self.bib.write_text(
            "@article{paper2026,\n"
            "  title = {A Bootstrap Paper},\n"
            "  author = {Author, A.},\n"
            "  year = {2026},\n"
            "  doi = {10.1000/bootstrap},\n"
            f"  file = {{{self.pdf.as_posix()}}}\n"
            "}\n",
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _args(self, **overrides):
        base = {
            "rag_dir": str(self.rag_dir),
            "bib": str(self.bib),
            "zip": "",
            "query": "",
            "record_id": "",
            "pdf_dir": "",
            "limit": 5,
            "select": 1,
            "enrich_inspire": False,
            "ingest": "none",
            "fallback_pdf_on_arxiv_fail": False,
            "strict_evidence": False,
            "strict_lint": False,
            "dry_run": True,
            "yes": False,
        }
        base.update(overrides)
        return Namespace(**base)

    def test_dry_run_has_no_side_effects(self):
        result = bootstrap(self._args())

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["import_plan"]["summary"]["new_entries"], 1)
        self.assertFalse(self.rag_dir.exists())

    @patch("import_pipeline.download_arxiv_pdf")
    def test_yes_initializes_and_imports_without_ingest(self, download_arxiv_pdf):
        result = bootstrap(self._args(dry_run=False, yes=True))

        self.assertFalse(result["dry_run"])
        self.assertEqual(result["applied"]["appended"], 1)
        self.assertEqual(result["evidence"]["processed"], 0)
        self.assertEqual(result["lint"]["issues"], [])
        self.assertTrue((self.rag_dir / "template.md").exists())
        self.assertTrue((self.rag_dir / "summary" / "sources" / "paper2026.md").exists())
        self.assertEqual(len(parse_bibtex_file(self.rag_dir / "references.bib")), 1)
        download_arxiv_pdf.assert_not_called()


if __name__ == "__main__":
    unittest.main()
