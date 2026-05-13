"""Tests for unified RAG entry deletion."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from bib_parser import parse_bibtex_file, render_bibtex
from common import ensure_rag_dirs, write_frontmatter
from darw_schema import chunk_manifest_path, parsed_manifest_path, parsed_markdown_path
from delete_entry import apply_delete_plan, build_delete_plan
from source_page_builder import default_frontmatter


class TestDeleteEntry(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir)
        self.entry = {
            "ENTRYTYPE": "article",
            "ID": "paper2026",
            "title": "Delete Me Carefully",
            "author": "Author, A.",
            "year": "2026",
            "doi": "10.1000/delete",
            "eprint": "2603.24450",
        }
        other = {
            "ENTRYTYPE": "article",
            "ID": "other2026",
            "title": "Delete Me Carefully Extended",
            "author": "Other, B.",
            "year": "2026",
            "doi": "10.1000/other",
        }
        (self.rag_dir / "references.bib").write_text(
            render_bibtex(self.entry) + "\n\n" + render_bibtex(other) + "\n",
            encoding="utf-8",
        )
        self._write_source(self.entry)
        self._write_artifacts()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_source(self, entry):
        fm = default_frontmatter(entry, self.rag_dir)
        fm["edges"]["techniques"] = [{"canonical_id": "local:test", "label": "Test"}]
        source_path = self.rag_dir / "summary" / "sources" / f"{entry['ID']}.md"
        source_path.write_text(write_frontmatter(fm) + "\n# Delete Me Carefully\n", encoding="utf-8")
        index = self.rag_dir / "summary" / "techniques" / "local_test.md"
        index.parent.mkdir(parents=True, exist_ok=True)
        index.write_text(
            "---\ntype: edge-index\n---\n\n"
            "<!-- AUTO:BEGIN -->\n"
            "## Source pages (1)\n"
            "- [[../sources/paper2026]]\n"
            "<!-- AUTO:END -->\n",
            encoding="utf-8",
        )
        synth = self.rag_dir / "summary" / "synthesis" / "manual.md"
        synth.write_text("Manual prose cites [[../sources/paper2026]] and should be reviewed.\n", encoding="utf-8")

    def _write_artifacts(self):
        key = self.entry["ID"]
        doc_id = "arxiv:2603.24450"
        (self.rag_dir / "reference" / "pdfs" / f"{key}.pdf").write_bytes(b"%PDF-1.4\n%%EOF")
        parsed_markdown_path(self.rag_dir, doc_id).write_text("# Parsed\n", encoding="utf-8")
        parsed_manifest_path(self.rag_dir, doc_id).write_text(json.dumps({"doc_id": doc_id}), encoding="utf-8")
        chunk_manifest_path(self.rag_dir, doc_id).write_text(json.dumps({"chunk_id": "c1"}) + "\n", encoding="utf-8")

    def test_build_plan_by_key(self):
        plan = build_delete_plan(self.rag_dir, key="paper2026")

        self.assertEqual(plan.key, "paper2026")
        self.assertIn("source_page", plan.files)
        self.assertIn("pdf", plan.files)
        self.assertIn("parsed_markdown", plan.files)
        self.assertTrue(plan.markdown_references)

    def test_build_plan_by_doi_and_arxiv(self):
        by_doi = build_delete_plan(self.rag_dir, doi="10.1000/delete")
        by_arxiv = build_delete_plan(self.rag_dir, arxiv="2603.24450")

        self.assertEqual(by_doi.key, "paper2026")
        self.assertEqual(by_arxiv.key, "paper2026")

    def test_title_ambiguous_requires_review(self):
        plan = build_delete_plan(self.rag_dir, title="Delete Me Carefully")

        self.assertTrue(plan.errors)
        self.assertGreaterEqual(len(plan.ambiguous), 2)

    def test_dry_run_plan_has_no_side_effects(self):
        before_manifest = (self.rag_dir / "references.bib").read_text(encoding="utf-8")
        plan = build_delete_plan(self.rag_dir, key="paper2026")

        self.assertTrue((self.rag_dir / "summary" / "sources" / "paper2026.md").exists())
        self.assertEqual((self.rag_dir / "references.bib").read_text(encoding="utf-8"), before_manifest)
        self.assertIn("source_page", plan.files)

    def test_apply_deletes_entry_artifacts_and_logs(self):
        plan = build_delete_plan(self.rag_dir, key="paper2026")
        result = apply_delete_plan(plan)

        self.assertEqual(result["manifest_changed"], 1)
        self.assertFalse((self.rag_dir / "summary" / "sources" / "paper2026.md").exists())
        self.assertFalse((self.rag_dir / "reference" / "pdfs" / "paper2026.pdf").exists())
        self.assertFalse(parsed_markdown_path(self.rag_dir, "arxiv:2603.24450").exists())
        entries = parse_bibtex_file(self.rag_dir / "references.bib")
        self.assertEqual([entry["ID"] for entry in entries], ["other2026"])
        self.assertIn("delete-entry", (self.rag_dir / "log.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
