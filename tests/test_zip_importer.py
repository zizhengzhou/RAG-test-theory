"""Tests for zip_importer — RDF parsing, PDF attachment resolution, dedup.

Integration tests use the zotero-rdf-minimal fixture to verify the
zip_importer pipeline without touching the real RAG directory.
"""

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from pdf_validator import is_pdf
from rdf_parser import parse_rdf

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestZipImporter(unittest.TestCase):
    """Tests for RDF parsing and attachment validation used by zip_importer."""

    def test_parses_rdf_from_fixture(self):
        """The RDF fixture should parse into at least one entry with required fields."""
        rdf_path = FIXTURES / "zotero-rdf-minimal" / "exported-items.rdf"
        self.assertTrue(rdf_path.exists(), f"RDF fixture missing: {rdf_path}")
        items = parse_rdf(rdf_path)
        self.assertIsInstance(items, list)
        self.assertGreater(len(items), 0, "Expected at least one entry from RDF fixture")
        for item in items:
            self.assertIn("title", item)
            self.assertIn("authors", item)
            self.assertIn("identifiers", item)

    def test_rdf_entry_has_attachments(self):
        """Entries from the RDF fixture should include attachment metadata."""
        rdf_path = FIXTURES / "zotero-rdf-minimal" / "exported-items.rdf"
        items = parse_rdf(rdf_path)
        for item in items:
            self.assertIn("attachments", item,
                          f"Entry '{item.get('title', '?')}' missing 'attachments' key")
            for att in item["attachments"]:
                self.assertIn("path", att)
                self.assertIn("type", att)

    def test_pdf_attachment_is_valid(self):
        """The PDF fixture should be recognized as a valid PDF."""
        pdf = FIXTURES / "zotero-rdf-minimal" / "files" / "1" / "paper.pdf"
        self.assertTrue(pdf.exists(), f"PDF fixture missing: {pdf}")
        self.assertTrue(is_pdf(pdf))

    def test_html_attachment_is_not_pdf(self):
        """HTML snapshots should be rejected by is_pdf."""
        html = FIXTURES / "zotero-rdf-minimal" / "files" / "2" / "snapshot.html"
        self.assertTrue(html.exists(), f"HTML fixture missing: {html}")
        self.assertFalse(is_pdf(html))

    def test_zip_structure_contains_expected_files(self):
        """A zipped RDF export should contain the RDF, PDF, and HTML files."""
        rdf_root = FIXTURES / "zotero-rdf-minimal"
        tf = tempfile.mktemp(suffix=".zip")
        try:
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


class TestZipImporterDryRun(unittest.TestCase):
    """Verify dry-run has no side effects — tests the zip_importer CLI."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        from common import ensure_rag_dirs
        ensure_rag_dirs(self.rag_dir, ())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dry_run_writes_nothing(self):
        """Running zip_importer --dry-run should create no files."""
        import subprocess
        rdf_root = FIXTURES / "zotero-rdf-minimal"
        zip_path = self.tmp / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(rdf_root / "exported-items.rdf", "exported-items.rdf")
            zf.write(rdf_root / "files" / "1" / "paper.pdf", "files/1/paper.pdf")
            zf.write(rdf_root / "files" / "2" / "snapshot.html", "files/2/snapshot.html")

        zip_importer = str(Path(__file__).resolve().parents[1] / "scripts" / "rag" / "zip_importer.py")
        result = subprocess.run(
            [sys.executable, zip_importer, "--zip", str(zip_path), "--rag-dir", str(self.rag_dir), "--dry-run"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(result.returncode, 0, f"zip_importer failed: {result.stderr}")

        # No files should be written in dry-run mode
        bib = self.rag_dir / "references.bib"
        self.assertFalse(bib.exists(), f"references.bib should not exist after dry-run, got: {bib}")
        pdfs = list((self.rag_dir / "reference" / "pdfs").glob("*.pdf"))
        self.assertEqual(len(pdfs), 0, f"No PDFs should be copied in dry-run, got: {pdfs}")


if __name__ == "__main__":
    unittest.main()
