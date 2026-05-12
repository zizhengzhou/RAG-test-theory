"""Tests for DARW source resolution."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from common import ensure_rag_dirs
from resolve_source import resolve_entry


class TestResolveSource(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir, ())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_arxiv_eprint_resolves_to_arxiv_source(self):
        resolved = resolve_entry(
            {"ID": "smith2023", "title": "T", "eprint": "2301.12345"},
            self.rag_dir,
        )
        self.assertEqual(resolved.route, "arxiv_source")
        self.assertEqual(resolved.doc_id, "arxiv:2301.12345")

    def test_datacite_arxiv_doi_resolves_to_arxiv_source(self):
        resolved = resolve_entry(
            {"ID": "arxivdoi", "title": "T", "doi": "10.48550/arXiv.2603.24450"},
            self.rag_dir,
        )
        self.assertEqual(resolved.route, "arxiv_source")
        self.assertEqual(resolved.arxiv_id, "2603.24450")

    def test_pdf_only_resolves_to_pdf_pymupdf(self):
        pdf = self.rag_dir / "reference" / "pdfs" / "paper.pdf"
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
        resolved = resolve_entry({"ID": "paper", "title": "T", "doi": "10.1234/example"}, self.rag_dir)
        self.assertEqual(resolved.route, "pdf_pymupdf")
        self.assertEqual(resolved.doc_id, "10.1234/example")
        self.assertTrue(resolved.pdf_path.endswith("paper.pdf"))

    def test_unresolved_without_arxiv_or_pdf(self):
        resolved = resolve_entry({"ID": "missing", "title": "T"}, self.rag_dir)
        self.assertEqual(resolved.route, "")
        self.assertTrue(resolved.needs_review)


if __name__ == "__main__":
    unittest.main()
