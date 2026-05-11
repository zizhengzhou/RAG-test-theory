"""Tests for provider-backed search-and-add."""

import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from common import ensure_rag_dirs
from search_add import command_add


class TestSearchAdd(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir, ["methods"])
        (self.rag_dir / "references.bib").write_text("", encoding="utf-8")
        (self.rag_dir / "template.md").write_text(
            "---\n"
            "type: source\n"
            "methods: []\n"
            "---\n\n"
            "## summary\n\n"
            "_To be filled._\n",
            encoding="utf-8",
        )
        (self.rag_dir / "vocabulary.md").write_text(
            "# Vocabulary\n\n"
            "## methods\n"
            "- uncategorized\n",
            encoding="utf-8",
        )
        self.result = Namespace(
            record_id="12345",
            title="Search Add Paper",
            year="2026",
            authors=["A. Author", "B. Writer"],
            doi="10.1000/test",
            arxiv="2603.24450",
            pdf_url="https://arxiv.org/pdf/2603.24450.pdf",
        )
        self.bibtex = (
            "@article{test2026paper,\n"
            "  title = {Search Add Paper},\n"
            "  author = {Author, A. and Writer, B.},\n"
            "  year = {2026},\n"
            "  eprint = {2603.24450},\n"
            "  doi = {10.1000/test}\n"
            "}\n"
        )

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def _args(self, **overrides):
        base = {
            "rag_dir": str(self.rag_dir),
            "query": "arxiv:2603.24450",
            "record_id": "",
            "select": 1,
            "limit": 5,
            "dry_run": False,
            "yes": False,
        }
        base.update(overrides)
        return Namespace(**base)

    @patch("search_add.fetch_inspire_bibtex")
    @patch("search_add._select_result")
    def test_add_dry_run_has_no_side_effects(self, select_result, fetch_bibtex):
        select_result.return_value = self.result
        fetch_bibtex.return_value = self.bibtex
        args = self._args(dry_run=True)

        with patch("builtins.print") as printed:
            result = command_add(args)

        self.assertEqual(result, 0)
        self.assertEqual((self.rag_dir / "references.bib").read_text(encoding="utf-8"), "")
        self.assertFalse((self.rag_dir / "summary" / "sources" / "test2026paper.md").exists())
        output = "\n".join(str(call.args[0]) for call in printed.call_args_list)
        self.assertIn("[dry-run] no files written", output)

    @patch("search_add.download_arxiv_pdf")
    @patch("search_add.fetch_inspire_bibtex")
    @patch("search_add._select_result")
    def test_add_yes_writes_manifest_source_and_pdf(self, select_result, fetch_bibtex, download_pdf):
        select_result.return_value = self.result
        fetch_bibtex.return_value = self.bibtex
        download_pdf.side_effect = lambda arxiv, out_path, dry_run=False: out_path.write_bytes(b"%PDF-1.4\n%%EOF")
        args = self._args(yes=True)

        with patch("builtins.print"):
            result = command_add(args)

        self.assertEqual(result, 0)
        manifest = (self.rag_dir / "references.bib").read_text(encoding="utf-8")
        self.assertIn("@article{test2026paper", manifest)
        source_path = self.rag_dir / "summary" / "sources" / "test2026paper.md"
        self.assertTrue(source_path.exists())
        self.assertIn("Search Add Paper", source_path.read_text(encoding="utf-8"))
        pdf_path = self.rag_dir / "reference" / "pdfs" / "test2026paper.pdf"
        self.assertTrue(pdf_path.exists())
        download_pdf.assert_called_once()

    @patch("search_add.download_arxiv_pdf")
    @patch("search_add.fetch_inspire_bibtex")
    @patch("search_add._select_result")
    def test_add_duplicate_reuses_existing_key(self, select_result, fetch_bibtex, download_pdf):
        (self.rag_dir / "references.bib").write_text(
            "@article{existing2026paper,\n"
            "  title = {Search Add Paper},\n"
            "  author = {Author, A. and Writer, B.},\n"
            "  year = {2026},\n"
            "  eprint = {2603.24450},\n"
            "  doi = {10.1000/test}\n"
            "}\n",
            encoding="utf-8",
        )
        select_result.return_value = self.result
        fetch_bibtex.return_value = self.bibtex
        download_pdf.side_effect = lambda arxiv, out_path, dry_run=False: out_path.write_bytes(b"%PDF-1.4\n%%EOF")
        args = self._args(yes=True)

        with patch("builtins.print") as printed:
            result = command_add(args)

        self.assertEqual(result, 0)
        manifest = (self.rag_dir / "references.bib").read_text(encoding="utf-8")
        self.assertNotIn("test2026paper", manifest)
        source_path = self.rag_dir / "summary" / "sources" / "existing2026paper.md"
        self.assertTrue(source_path.exists())
        pdf_path = self.rag_dir / "reference" / "pdfs" / "existing2026paper.pdf"
        self.assertTrue(pdf_path.exists())
        output = "\n".join(str(call.args[0]) for call in printed.call_args_list)
        self.assertIn("duplicate=True", output)

    @patch("search_add.download_arxiv_pdf")
    @patch("search_add.fetch_inspire_bibtex")
    @patch("search_add._select_result")
    def test_add_skips_pdf_download_without_arxiv(self, select_result, fetch_bibtex, download_pdf):
        result_without_arxiv = Namespace(
            record_id="12345",
            title="Search Add Paper",
            year="2026",
            authors=["A. Author"],
            doi="10.1000/test",
            arxiv="",
            pdf_url="",
        )
        select_result.return_value = result_without_arxiv
        fetch_bibtex.return_value = (
            "@article{test2026paper,\n"
            "  title = {Search Add Paper},\n"
            "  author = {Author, A.},\n"
            "  year = {2026},\n"
            "  doi = {10.1000/test}\n"
            "}\n"
        )
        args = self._args(yes=True)

        with patch("builtins.print"):
            result = command_add(args)

        self.assertEqual(result, 0)
        download_pdf.assert_not_called()
        self.assertFalse((self.rag_dir / "reference" / "pdfs" / "test2026paper.pdf").exists())


if __name__ == "__main__":
    unittest.main()
