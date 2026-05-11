"""Tests for pdf_validator."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))
from pdf_validator import is_pdf

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestPdfValidator(unittest.TestCase):
    def test_valid_pdf(self):
        self.assertTrue(is_pdf(FIXTURES / "zotero-rdf-minimal" / "files" / "1" / "paper.pdf"))

    def test_html_is_not_pdf(self):
        self.assertFalse(is_pdf(FIXTURES / "zotero-rdf-minimal" / "files" / "2" / "snapshot.html"))

    def test_missing_file(self):
        self.assertFalse(is_pdf(Path("nonexistent.pdf")))


if __name__ == "__main__":
    unittest.main()
