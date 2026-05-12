"""Tests for DARW evidence removal."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from bib_parser import render_bibtex
from common import ensure_rag_dirs
from evidence_ingest import ingest_entry
from remove_evidence import find_evidence_files, plan_removal, remove_evidence


class TestRemoveEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir, ())
        self.entry = {
            "ENTRYTYPE": "article",
            "ID": "paper",
            "title": "Evidence Paper",
            "author": "Smith, Alice",
            "year": "2024",
            "eprint": "2401.12345",
        }
        (self.rag_dir / "references.bib").write_text(render_bibtex(self.entry), encoding="utf-8")
        self.parsed = self.tmp / "parsed.md"
        self.parsed.write_text(
            "# Intro\n\nRaw evidence text with TLS noise.\n",
            encoding="utf-8",
        )
        ingest_entry(self.entry, self.rag_dir, arxiv_output=self.parsed)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dry_run_does_not_delete_files(self):
        before_files = list((self.rag_dir / "reference" / "chunks").glob("*.jsonl"))
        self.assertTrue(len(before_files) > 0)
        sp = self.rag_dir / "summary" / "sources" / "paper.md"
        before_source = sp.read_text(encoding="utf-8")
        result = remove_evidence(self.rag_dir, "paper", dry_run=True)
        after_files = list((self.rag_dir / "reference" / "chunks").glob("*.jsonl"))
        self.assertTrue(len(after_files) > 0)
        self.assertEqual(sp.read_text(encoding="utf-8"), before_source)
        self.assertIn("dry-run", result["log"][0])

    def test_remove_deletes_evidence_files(self):
        self.assertTrue((self.rag_dir / "reference" / "parsed").exists())
        self.assertTrue((self.rag_dir / "reference" / "chunks").exists())
        result = remove_evidence(self.rag_dir, "paper", dry_run=False)
        self.assertTrue(len(result["log"]) > 0)
        # Chunk file should be gone
        chunk_files = list((self.rag_dir / "reference" / "chunks").glob("*.jsonl"))
        self.assertEqual(len(chunk_files), 0)
        # Parsed markdown should be gone
        md_files = list((self.rag_dir / "reference" / "parsed").glob("*.md"))
        self.assertEqual(len(md_files), 0)
        # Manifest should be gone
        manifest_files = list((self.rag_dir / "reference" / "parsed").glob("*.manifest.json"))
        self.assertEqual(len(manifest_files), 0)

    def test_plan_finds_all_evidence_files(self):
        plan = plan_removal(self.rag_dir, "paper")
        self.assertIn("parsed_md", plan["files"])
        self.assertIn("parsed_manifest", plan["files"])
        self.assertIn("chunk_manifest", plan["files"])
        self.assertIn("source_page", plan["files"])

    def test_plan_missing_key_returns_empty(self):
        plan = plan_removal(self.rag_dir, "nonexistent")
        self.assertEqual(len(plan["files"]), 0)

    def test_remove_cleans_source_page_links(self):
        # Add evidence links inside the nested YAML frontmatter (realistic structure)
        sp = self.rag_dir / "summary" / "sources" / "paper.md"
        content = sp.read_text(encoding="utf-8")
        content = content.replace(
            "  primary_evidence: ''\n",
            "  primary_evidence: reference/parsed/something.md\n",
        )
        content = content.replace(
            "chunk_manifest: ''\n",
            "chunk_manifest: reference/chunks/something.jsonl\n",
        )
        sp.write_text(content, encoding="utf-8")

        remove_evidence(self.rag_dir, "paper", dry_run=False)
        cleaned = sp.read_text(encoding="utf-8")
        self.assertNotIn("reference/parsed/something.md", cleaned)
        self.assertNotIn("reference/chunks/something.jsonl", cleaned)


if __name__ == "__main__":
    unittest.main()
