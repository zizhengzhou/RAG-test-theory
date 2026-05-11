"""Tests for RAG search/export CLI helpers."""

import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from bib_parser import render_bibtex
from common import ensure_rag_dirs
from export import command_export_bibtex, command_export_reading_list, command_get_bibtex, local_search


class TestExport(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir, ["methods"])
        entries = [
            {
                "ENTRYTYPE": "article",
                "ID": "smith2023benchmark",
                "title": "A Benchmark Study of Numeric Methods for Quantum Scattering",
                "author": "Smith, Alice and Jones, Bob",
                "year": "2023",
                "doi": "10.1234/jcp.2023.112345",
            },
            {
                "ENTRYTYPE": "article",
                "ID": "chen2024improved",
                "title": "Improved Coupled-Channel Analysis of Breakup Reactions",
                "author": "Chen, Wei and Tanaka, Hiroshi",
                "year": "2024",
                "eprint": "2401.00001",
            },
        ]
        (self.rag_dir / "references.bib").write_text("\n\n".join(render_bibtex(e) for e in entries), encoding="utf-8")
        sources = self.rag_dir / "summary" / "sources"
        sources.mkdir(parents=True, exist_ok=True)
        (sources / "chen2024improved.md").write_text(
            "---\ntype: source\ntitle: Improved Coupled-Channel Analysis of Breakup Reactions\nmethods: [coupled-channel]\npdf: ../../reference/pdfs/chen2024improved.pdf\n---\n\n# Chen\n\n## Summary\n\nBreakup reaction analysis.\n",
            encoding="utf-8",
        )
        pdf_dir = self.rag_dir / "reference" / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        (pdf_dir / "chen2024improved.pdf").write_bytes(b"%PDF-1.4\n%%EOF")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_local_search_finds_query_candidate(self):
        results = local_search(self.rag_dir, ["coupled-channel"], limit=5)
        self.assertEqual(results[0].key, "chen2024improved")
        self.assertGreater(results[0].score, 0)

    def test_local_search_filters_by_tag(self):
        results = local_search(self.rag_dir, [], tags=["methods=coupled-channel"], limit=5)
        self.assertEqual([r.key for r in results], ["chen2024improved"])

    def test_get_bibtex_fallback_local(self):
        args = Namespace(
            rag_dir=str(self.rag_dir),
            query=[],
            key=["smith2023benchmark"],
            tag=[],
            limit=5,
            provider="local",
            fallback_local=True,
            format="bibtex",
        )
        with patch("builtins.print") as printed:
            result = command_get_bibtex(args)
        self.assertEqual(result, 0)
        output = "\n".join(str(call.args[0]) for call in printed.call_args_list)
        self.assertIn("@article{smith2023benchmark", output)

    def test_export_bibtex_uses_inspire_when_available(self):
        args = Namespace(
            rag_dir=str(self.rag_dir),
            query=[],
            key=["chen2024improved"],
            tag=[],
            limit=5,
            provider="inspire",
            fallback_local=False,
            out="",
        )
        with patch("export._inspire_results_for_candidate") as results, patch("export.fetch_inspire_bibtex", return_value="@article{INSPIRE:canonical,}"):
            results.return_value = [Namespace(record_id="123")]
            with patch("builtins.print") as printed:
                result = command_export_bibtex(args)
        self.assertEqual(result, 0)
        output = "\n".join(str(call.args[0]) for call in printed.call_args_list)
        self.assertIn("INSPIRE:canonical", output)

    def test_export_reading_list_contains_links(self):
        args = Namespace(
            rag_dir=str(self.rag_dir),
            query=[],
            key=["chen2024improved"],
            tag=[],
            limit=5,
            provider="local",
            out="",
        )
        with patch("builtins.print") as printed:
            result = command_export_reading_list(args)
        self.assertEqual(result, 0)
        output = "\n".join(str(call.args[0]) for call in printed.call_args_list)
        self.assertIn("# Reading List", output)
        self.assertIn("summary/sources/chen2024improved.md", output)
        self.assertIn("reference/pdfs/chen2024improved.pdf", output)


if __name__ == "__main__":
    unittest.main()
