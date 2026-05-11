"""Tests for provider-backed PDF downloads."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from pdf_downloader import download_arxiv_pdf, download_pdf


class _FakeHeaders(dict):
    def get(self, key, default=None):
        return super().get(key.lower(), default)


class _FakeResponse:
    def __init__(self, data: bytes, content_type: str):
        self._data = data
        self.headers = _FakeHeaders({"content-type": content_type})

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestPdfDownloader(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.out = self.tmp / "paper.pdf"
        self.valid_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_download_pdf_dry_run_has_no_side_effects(self):
        result = download_pdf("https://example.test/paper.pdf", self.out, dry_run=True)
        self.assertTrue(result)
        self.assertFalse(self.out.exists())

    def test_download_pdf_writes_valid_pdf(self):
        with patch("pdf_downloader.urllib.request.urlopen", return_value=_FakeResponse(self.valid_pdf, "application/pdf")):
            result = download_pdf("https://example.test/paper.pdf", self.out)
        self.assertTrue(result)
        self.assertEqual(self.out.read_bytes(), self.valid_pdf)

    def test_download_pdf_rejects_non_pdf_content(self):
        with patch("pdf_downloader.urllib.request.urlopen", return_value=_FakeResponse(b"not a pdf", "text/html")):
            with self.assertRaisesRegex(ValueError, "not a PDF"):
                download_pdf("https://example.test/paper.pdf", self.out)
        self.assertFalse(self.out.exists())

    def test_download_arxiv_pdf_uses_canonical_url(self):
        with patch("pdf_downloader.urllib.request.urlopen", return_value=_FakeResponse(self.valid_pdf, "application/pdf")) as mocked:
            result = download_arxiv_pdf("2603.24450", self.out)
        self.assertTrue(result)
        request = mocked.call_args.args[0]
        self.assertEqual(request.full_url, "https://arxiv.org/pdf/2603.24450.pdf")

    def test_download_arxiv_pdf_requires_identifier(self):
        with self.assertRaisesRegex(ValueError, "no arXiv id available"):
            download_arxiv_pdf("", self.out)


if __name__ == "__main__":
    unittest.main()
