"""Tests for evidence-grounded source summary drafting."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from common import ensure_rag_dirs, write_frontmatter
from summarize_evidence import draft_summary_from_chunks, summarize_source_page


class TestSummarizeEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir, ())
        self.source = self.rag_dir / "summary" / "sources" / "paper.md"
        fm = {"schema_version": "darw-source-v1", "citation_key": "paper"}
        self.source.write_text(write_frontmatter(fm) + "# Paper\n\n## One-line contribution\n\n_To be filled._\n", encoding="utf-8")
        chunk = {
            "chunk_id": "doc::intro::chunk-001-abc",
            "citation_key": "paper",
            "section_title": "Intro",
            "section_anchor": "#intro",
            "text": "This paper demonstrates a superconducting detector with improved noise performance. More details follow.",
            "equation_ids": [],
        }
        (self.rag_dir / "reference" / "chunks" / "doc.jsonl").write_text(json.dumps(chunk) + "\n", encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_draft_summary_contains_chunk_id(self):
        draft = draft_summary_from_chunks([{
            "chunk_id": "c1",
            "text": "Evidence sentence supports the summary. Another sentence.",
            "section_anchor": "#intro",
            "equation_ids": [],
        }])
        self.assertIn("c1", draft["key results"])

    def test_summarize_source_page_applies_with_yes_mode(self):
        self.assertTrue(summarize_source_page(self.rag_dir, "paper", dry_run=False))
        text = self.source.read_text(encoding="utf-8")
        self.assertIn("doc::intro::chunk-001-abc", text)
        self.assertIn("Draft from evidence chunks", text)


if __name__ == "__main__":
    unittest.main()
