"""Tests for RAG update merge reports."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from bib_parser import render_bibtex
from common import ensure_rag_dirs, write_frontmatter
from merge_rag_update import build_merge_report


class TestMergeRagUpdate(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.base = self.tmp / "base"
        self.update = self.tmp / "update"
        for rag in (self.base, self.update):
            ensure_rag_dirs(rag)
            entry = {"ENTRYTYPE": "article", "ID": "paper", "title": "T", "year": "2024"}
            (rag / "references.bib").write_text(render_bibtex(entry), encoding="utf-8")
            (rag / "summary" / "sources" / "paper.md").write_text(
                write_frontmatter({"doc_id": "arxiv:2401.12345"}) + "# T\n",
                encoding="utf-8",
            )
            (rag / "vocabulary.md").write_text("# vocab\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_merge_report_flags_duplicates(self):
        report = build_merge_report(self.base, self.update)

        self.assertIn("paper", report["duplicate_citation_keys"])
        self.assertTrue(report["duplicate_doc_ids"])
        self.assertTrue(report["manual_review"])


if __name__ == "__main__":
    unittest.main()
