"""Tests for the unified import pipeline."""

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
from common import ensure_rag_dirs
from external_search import SearchResult
from import_pipeline import apply_plan, build_plan, plan_as_dict


FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestImportPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _args(self, **overrides):
        base = {
            "rag_dir": str(self.rag_dir),
            "bib": "",
            "zip": "",
            "query": "",
            "record_id": "",
            "pdf_dir": "",
            "limit": 5,
            "select": 1,
            "enrich_inspire": False,
        }
        base.update(overrides)
        return Namespace(**base)

    def test_bib_dry_run_plan_reports_new_and_duplicate_without_writes(self):
        ensure_rag_dirs(self.rag_dir)
        (self.rag_dir / "references.bib").write_text(
            "@article{existing2023,\n"
            "  title = {A Benchmark Study of Numeric Methods for Quantum Scattering},\n"
            "  author = {Smith, Alice and Jones, Bob},\n"
            "  year = {2023},\n"
            "  doi = {10.1234/jcp.2023.112345}\n"
            "}\n",
            encoding="utf-8",
        )

        plan = build_plan(self._args(bib=str(FIXTURES / "sample.bib")))
        data = plan_as_dict(plan)

        self.assertEqual(data["summary"]["candidates"], 3)
        self.assertEqual(data["summary"]["new_entries"], 2)
        self.assertEqual(data["summary"]["duplicates"], 1)
        duplicate_items = [item for item in data["items"] if item["duplicate_of"]]
        self.assertEqual(duplicate_items[0]["duplicate_of"], "existing2023")
        self.assertEqual(duplicate_items[0]["duplicate_match"], "doi:10.1234/jcp.2023.112345")
        self.assertFalse((self.rag_dir / "summary" / "sources" / "chen2024improved.md").exists())
        self.assertFalse((self.rag_dir / "log.md").exists())

    @patch("import_pipeline.download_arxiv_pdf")
    def test_bib_yes_appends_manifest_and_creates_source_pages(self, download_arxiv_pdf):
        download_arxiv_pdf.side_effect = lambda arxiv, out_path, dry_run=False: out_path.write_bytes(b"%PDF-1.4\n%%EOF")
        ensure_rag_dirs(self.rag_dir)
        (self.rag_dir / "references.bib").write_text("", encoding="utf-8")
        plan = build_plan(self._args(bib=str(FIXTURES / "sample.bib")))

        result = apply_plan(plan)

        self.assertEqual(result["appended"], 3)
        entries = parse_bibtex_file(self.rag_dir / "references.bib")
        self.assertEqual(len(entries), 3)
        self.assertTrue((self.rag_dir / "summary" / "sources" / "smith2023benchmark.md").exists())
        self.assertTrue((self.rag_dir / "log.md").exists())

    @patch("import_pipeline.download_arxiv_pdf")
    def test_existing_target_pdf_is_not_downloaded_even_with_arxiv(self, download_arxiv_pdf):
        ensure_rag_dirs(self.rag_dir)
        pdf_target = self.rag_dir / "reference" / "pdfs" / "local2026paper.pdf"
        pdf_target.parent.mkdir(parents=True, exist_ok=True)
        pdf_target.write_bytes(b"%PDF-1.4\n%%EOF")
        bib_path = self.tmp / "local2026.bib"
        bib_path.write_text(
            "@article{local2026paper,\n"
            "  title = {Local Paper With Arxiv},\n"
            "  author = {Author, A.},\n"
            "  year = {2026},\n"
            "  eprint = {2601.00001}\n"
            "}\n",
            encoding="utf-8",
        )

        plan = build_plan(self._args(bib=str(bib_path)))
        data = plan_as_dict(plan)
        result = apply_plan(plan)

        self.assertEqual(data["items"][0]["pdf_action"], "exists")
        self.assertEqual(result["downloaded_pdfs"], 0)
        download_arxiv_pdf.assert_not_called()

    @patch("import_pipeline.download_arxiv_pdf")
    def test_pdf_dir_match_is_copied_instead_of_arxiv_download(self, download_arxiv_pdf):
        ensure_rag_dirs(self.rag_dir)
        source_dir = self.tmp / "pdfs"
        source_dir.mkdir()
        (source_dir / "local2026paper.pdf").write_bytes(b"%PDF-1.4\n%%EOF")
        bib_path = self.tmp / "local2026.bib"
        bib_path.write_text(
            "@article{local2026paper,\n"
            "  title = {Local Paper With Arxiv},\n"
            "  author = {Author, A.},\n"
            "  year = {2026},\n"
            "  eprint = {2601.00001}\n"
            "}\n",
            encoding="utf-8",
        )

        plan = build_plan(self._args(bib=str(bib_path), pdf_dir=str(source_dir)))
        data = plan_as_dict(plan)
        result = apply_plan(plan)

        self.assertEqual(data["items"][0]["pdf_action"], "copy")
        self.assertEqual(result["copied_pdfs"], 1)
        self.assertEqual(result["downloaded_pdfs"], 0)
        self.assertTrue((self.rag_dir / "reference" / "pdfs" / "local2026paper.pdf").exists())
        download_arxiv_pdf.assert_not_called()

    @patch("import_pipeline.download_arxiv_pdf")
    def test_bibtex_file_pdf_is_copied_instead_of_arxiv_download(self, download_arxiv_pdf):
        ensure_rag_dirs(self.rag_dir)
        source_pdf = self.tmp / "already-local.pdf"
        source_pdf.write_bytes(b"%PDF-1.4\n%%EOF")
        bib_path = self.tmp / "local2026.bib"
        bib_path.write_text(
            "@article{local2026paper,\n"
            "  title = {Local Paper With Arxiv},\n"
            "  author = {Author, A.},\n"
            "  year = {2026},\n"
            "  eprint = {2601.00001},\n"
            f"  file = {{{source_pdf.as_posix()}}}\n"
            "}\n",
            encoding="utf-8",
        )

        plan = build_plan(self._args(bib=str(bib_path)))
        data = plan_as_dict(plan)
        result = apply_plan(plan)

        self.assertEqual(data["items"][0]["pdf_action"], "copy")
        self.assertIn("matched BibTeX file PDF", "\n".join(data["items"][0]["notes"]))
        self.assertEqual(result["copied_pdfs"], 1)
        self.assertEqual(result["downloaded_pdfs"], 0)
        self.assertTrue((self.rag_dir / "reference" / "pdfs" / "local2026paper.pdf").exists())
        download_arxiv_pdf.assert_not_called()

    def test_zip_dry_run_plan_reports_pdf_copy_without_writes(self):
        plan = build_plan(self._args(zip=str(FIXTURES / "zotero-rdf-minimal.zip")))
        data = plan_as_dict(plan)

        self.assertEqual(data["summary"]["candidates"], 2)
        pdf_actions = {item["effective_key"]: item["pdf_action"] for item in data["items"]}
        self.assertEqual(pdf_actions["smith2023benchmark"], "copy")
        self.assertEqual(pdf_actions["chen2024improved"], "missing")
        self.assertFalse((self.rag_dir / "references.bib").exists())
        self.assertFalse((self.rag_dir / "reference").exists())

    @patch("import_pipeline.download_arxiv_pdf")
    def test_duplicate_zip_pdf_is_copied_to_existing_key_on_apply(self, download_arxiv_pdf):
        download_arxiv_pdf.side_effect = lambda arxiv, out_path, dry_run=False: out_path.write_bytes(b"%PDF-1.4\n%%EOF")
        ensure_rag_dirs(self.rag_dir)
        (self.rag_dir / "references.bib").write_text(
            "@article{existing2023,\n"
            "  title = {A Benchmark Study of Numeric Methods for Quantum Scattering},\n"
            "  author = {Smith, Alice and Jones, Bob},\n"
            "  year = {2023},\n"
            "  doi = {10.1234/jcp.2023.112345}\n"
            "}\n",
            encoding="utf-8",
        )

        plan = build_plan(self._args(zip=str(FIXTURES / "zotero-rdf-minimal.zip")))
        data = plan_as_dict(plan)
        smith = [item for item in data["items"] if item["effective_key"] == "existing2023"][0]
        self.assertEqual(smith["manifest_action"], "skip-duplicate")
        self.assertEqual(smith["pdf_action"], "copy")
        result = apply_plan(plan)

        self.assertEqual(result["copied_pdfs"], 1)
        self.assertTrue((self.rag_dir / "reference" / "pdfs" / "existing2023.pdf").exists())

    def test_same_key_different_paper_is_renamed_not_overwritten(self):
        ensure_rag_dirs(self.rag_dir)
        (self.rag_dir / "references.bib").write_text(
            "@article{smith2023benchmark,\n"
            "  title = {A Different Paper},\n"
            "  author = {Other, A.},\n"
            "  year = {2023},\n"
            "  doi = {10.9999/different}\n"
            "}\n",
            encoding="utf-8",
        )

        plan = build_plan(self._args(bib=str(FIXTURES / "sample.bib")))
        data = plan_as_dict(plan)

        renamed = [item for item in data["items"] if item["key"] == "smith2023benchmark-2"]
        self.assertEqual(len(renamed), 1)
        self.assertIn("renamed citation key conflict", "\n".join(renamed[0]["notes"]))

    @patch("import_pipeline.fetch_inspire_bibtex")
    @patch("import_pipeline.search_inspire")
    def test_search_dry_run_plan_uses_inspire_candidate(self, search_inspire, fetch_bibtex):
        search_inspire.return_value = [
            SearchResult(
                provider="inspire",
                record_id="12345",
                title="Search Add Paper",
                authors=["Author, A."],
                year="2026",
                doi="10.1000/test",
                arxiv="2603.24450",
                control_number="12345",
            )
        ]
        fetch_bibtex.return_value = (
            "@article{test2026paper,\n"
            "  title = {Search Add Paper},\n"
            "  author = {Author, A.},\n"
            "  year = {2026},\n"
            "  eprint = {2603.24450},\n"
            "  doi = {10.1000/test}\n"
            "}\n"
        )

        plan = build_plan(self._args(query="Search Add Paper"))
        data = plan_as_dict(plan)

        self.assertEqual(data["summary"]["new_entries"], 1)
        item = data["items"][0]
        self.assertEqual(item["effective_key"], "test2026paper")
        self.assertEqual(item["pdf_action"], "download-arxiv")
        self.assertEqual(item["record_id"], "12345")
        self.assertFalse((self.rag_dir / "references.bib").exists())

    @patch("bib_update.search_inspire_by_identifier")
    def test_enrich_inspire_plan_reports_bib_field_updates(self, search_identifier):
        search_identifier.return_value = [
            SearchResult(
                provider="inspire",
                record_id="12345",
                title="Improved Coupled-Channel Analysis of Breakup Reactions",
                authors=["Chen, Wei"],
                year="2024",
                doi="10.5678/prc.2024.024612",
                arxiv="2401.00001",
                control_number="12345",
            )
        ]

        plan = build_plan(self._args(bib=str(FIXTURES / "sample.bib"), enrich_inspire=True))
        data = plan_as_dict(plan)

        chen = [item for item in data["items"] if item["effective_key"] == "chen2024improved"][0]
        changes = {change["field"]: change["new"] for change in chen["bib_enrichment"]["changes"]}
        self.assertTrue(chen["bib_enrichment"]["enabled"])
        self.assertEqual(changes["eprint"], "2401.00001")


if __name__ == "__main__":
    unittest.main()
