"""Tests for safe BibTeX metadata update plans."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from bib_parser import parse_bibtex_file, render_bibtex
from bib_update import apply_update_plan, build_update_plan, plan_as_dict, plan_entry_update
from common import ensure_rag_dirs
from external_search import SearchResult


def inspire_result(**overrides):
    base = {
        "provider": "inspire",
        "record_id": "12345",
        "title": "DOI Only Paper",
        "authors": ["Author, A."],
        "year": "2026",
        "doi": "10.1000/test",
        "arxiv": "2603.24450",
        "control_number": "12345",
    }
    base.update(overrides)
    return SearchResult(**base)


class TestBibUpdate(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @patch("bib_update.search_inspire_by_identifier")
    def test_doi_only_entry_plans_eprint_and_inspire_updates(self, search_identifier):
        search_identifier.return_value = [inspire_result()]
        entry = {
            "ENTRYTYPE": "article",
            "ID": "doi2026",
            "title": "DOI Only Paper",
            "author": "Author, A.",
            "year": "2026",
            "doi": "10.1000/test",
        }

        update = plan_entry_update(entry)

        changes = {change.field: change.new for change in update.changes}
        self.assertEqual(changes["eprint"], "2603.24450")
        self.assertEqual(changes["inspire"], "12345")
        self.assertFalse(update.needs_review)

    @patch("bib_update.search_inspire_by_identifier")
    def test_conflicting_existing_arxiv_requires_review(self, search_identifier):
        search_identifier.return_value = [inspire_result(arxiv="2603.24450")]
        entry = {
            "ENTRYTYPE": "article",
            "ID": "conflict2026",
            "title": "Conflict Paper",
            "doi": "10.1000/test",
            "eprint": "2501.00001",
        }

        update = plan_entry_update(entry)

        self.assertTrue(update.needs_review)
        self.assertIn("eprint conflict", "\n".join(update.conflicts))

    @patch("bib_update.search_inspire_by_identifier")
    def test_multiple_candidates_require_review(self, search_identifier):
        search_identifier.return_value = [
            inspire_result(record_id="1", control_number="1"),
            inspire_result(record_id="2", control_number="2", arxiv="2603.24451"),
        ]
        entry = {
            "ENTRYTYPE": "article",
            "ID": "multi2026",
            "title": "Multi Paper",
            "doi": "10.1000/test",
        }

        update = plan_entry_update(entry)

        self.assertTrue(update.needs_review)
        self.assertIn("multiple INSPIRE candidates", update.conflicts)

    @patch("bib_update.search_inspire_by_identifier")
    def test_apply_update_plan_rewrites_manifest_and_logs(self, search_identifier):
        search_identifier.return_value = [inspire_result()]
        manifest = self.rag_dir / "references.bib"
        manifest.write_text(
            render_bibtex(
                {
                    "ENTRYTYPE": "article",
                    "ID": "doi2026",
                    "title": "DOI Only Paper",
                    "author": "Author, A.",
                    "year": "2026",
                    "doi": "10.1000/test",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        plan = build_update_plan(self.rag_dir, key="doi2026")
        data = plan_as_dict(plan)
        self.assertEqual(data["summary"]["changed"], 1)
        updated = apply_update_plan(plan)

        self.assertEqual(updated, 1)
        entries = parse_bibtex_file(manifest)
        self.assertEqual(entries[0]["eprint"], "2603.24450")
        self.assertEqual(entries[0]["inspire"], "12345")
        self.assertIn("bib-update", (self.rag_dir / "log.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
