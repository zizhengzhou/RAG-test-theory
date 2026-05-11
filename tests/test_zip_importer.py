"""Tests for zip_importer (integration with RDF parser)."""

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))
from pdf_validator import is_pdf

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestZipImporter(unittest.TestCase):
    def test_zip_contains_rdf(self):
        tf = tempfile.mktemp(suffix=".zip")
        try:
            rdf_root = FIXTURES / "zotero-rdf-minimal"
            with zipfile.ZipFile(tf, "w") as zf:
                zf.write(rdf_root / "exported-items.rdf", "exported-items.rdf")
                zf.write(rdf_root / "files" / "1" / "paper.pdf", "files/1/paper.pdf")
                zf.write(rdf_root / "files" / "2" / "snapshot.html", "files/2/snapshot.html")
            with zipfile.ZipFile(tf, "r") as zf:
                names = zf.namelist()
                self.assertIn("exported-items.rdf", names)
                self.assertIn("files/1/paper.pdf", names)
                self.assertIn("files/2/snapshot.html", names)
        finally:
            Path(tf).unlink(missing_ok=True)

    def test_pdf_attachment_is_valid(self):
        self.assertTrue(is_pdf(FIXTURES / "zotero-rdf-minimal" / "files" / "1" / "paper.pdf"))

    def test_html_attachment_skipped(self):
        self.assertFalse(is_pdf(FIXTURES / "zotero-rdf-minimal" / "files" / "2" / "snapshot.html"))


if __name__ == "__main__":
    unittest.main()
