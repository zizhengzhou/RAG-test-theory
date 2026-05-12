"""Tests for DARW RAG maintenance commands."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from common import ensure_rag_dirs, write_frontmatter
from bib_parser import render_bibtex
from source_page_builder import default_frontmatter, body_skeleton
from update_index import collect_edge_tags, ensure_category_page, rebuild_auto_block


class TestRAGMaintain(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir, ())
        (self.rag_dir / "indexes").mkdir(parents=True, exist_ok=True)
        (self.rag_dir / "references.bib").write_text("", encoding="utf-8")
        (self.rag_dir / "vocabulary.md").write_text(
            "# DARW Vocabulary\n\n```yaml\nterms:\n"
            "  - canonical_id: \"local:uncategorized\"\n"
            "    label: \"Uncategorized\"\n"
            "    namespace: \"local\"\n"
            "    category: \"techniques\"\n"
            "    aliases: []\n"
            "    source: \"project\"\n"
            "    needs_review: true\n"
            "  - canonical_id: \"local:new-method\"\n"
            "    label: \"New Method\"\n"
            "    namespace: \"local\"\n"
            "    category: \"techniques\"\n"
            "    aliases: []\n"
            "    source: \"project\"\n"
            "    needs_review: true\n"
            "```\n",
            encoding="utf-8",
        )
        self.sample_entry = {
            "ENTRYTYPE": "article",
            "ID": "smith2023benchmark",
            "title": "A Benchmark Study of Numeric Methods for Quantum Scattering",
            "author": "Smith, Alice and Jones, Bob",
            "year": "2023",
            "doi": "10.1234/jcp.2023.112345",
        }
        (self.rag_dir / "references.bib").write_text(render_bibtex(self.sample_entry) + "\n", encoding="utf-8")
        self.source_path = self.rag_dir / "summary" / "sources" / "smith2023benchmark.md"
        fm = default_frontmatter(self.sample_entry, self.rag_dir)
        fm["edges"]["techniques"] = [{"canonical_id": "local:uncategorized", "label": "Uncategorized"}]
        body = "\n# A Benchmark Study of Numeric Methods for Quantum Scattering\n\n## Summary\n\nManual summary.\n\n## Key Findings\n\n- Finding.\n"
        self.source_path.write_text(write_frontmatter(fm) + body, encoding="utf-8")
        pdf_dir = self.rag_dir / "reference" / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        (pdf_dir / "smith2023benchmark.pdf").write_bytes(minimal_pdf_bytes())
        synth = self.rag_dir / "summary" / "synthesis" / "notes.md"
        synth.write_text("See [[../sources/smith2023benchmark]] for context.\n", encoding="utf-8")
        self._refresh_indexes()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def _refresh_indexes(self):
        tag_map = collect_edge_tags(self.rag_dir)
        for category, tags in tag_map.items():
            for tag, source_keys in tags.items():
                page = ensure_category_page(self.rag_dir, category, tag)
                rebuild_auto_block(page, category, tag, source_keys)

    def run_cli(self, *args):
        import subprocess

        return subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "rag" / "maintain.py"),
                *args,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_remove_dry_run_has_no_side_effects(self):
        result = self.run_cli("remove", "--rag-dir", str(self.rag_dir), "--key", "smith2023benchmark", "--dry-run")
        self.assertEqual(result.returncode, 0)
        self.assertIn("[dry-run] no files written", result.stdout)
        self.assertTrue(self.source_path.exists())
        self.assertTrue((self.rag_dir / "reference" / "pdfs" / "smith2023benchmark.pdf").exists())
        manifest = (self.rag_dir / "references.bib").read_text(encoding="utf-8")
        self.assertIn("smith2023benchmark", manifest)

    def test_remove_confirmed_removes_local_artifacts_and_keeps_synthesis(self):
        result = self.run_cli("remove", "--rag-dir", str(self.rag_dir), "--key", "smith2023benchmark", "--yes")
        self.assertEqual(result.returncode, 0)
        self.assertFalse(self.source_path.exists())
        self.assertFalse((self.rag_dir / "reference" / "pdfs" / "smith2023benchmark.pdf").exists())
        manifest = (self.rag_dir / "references.bib").read_text(encoding="utf-8")
        self.assertNotIn("smith2023benchmark", manifest)
        self.assertTrue((self.rag_dir / "summary" / "synthesis" / "notes.md").exists())
        self.assertIn("manual review", result.stdout.lower())

    def test_update_source_updates_fields(self):
        result = self.run_cli(
            "update-source",
            "--rag-dir", str(self.rag_dir),
            "--key", "smith2023benchmark",
            "--set", "source.title=Updated Title",
            "--yes",
        )
        self.assertEqual(result.returncode, 0)
        text = self.source_path.read_text(encoding="utf-8")
        self.assertIn("Updated Title", text)
        self.assertIn("Manual summary.", text)

    def test_reingest_preserves_body_and_adds_missing_defaults(self):
        text = self.source_path.read_text(encoding="utf-8")
        old_doi = "10.1234/jcp.2023.112345"
        # Remove the doi line entirely so the merge preserves the default
        text = text.replace(f"  doi: {old_doi}\n", "")
        self.source_path.write_text(text, encoding="utf-8")
        result = self.run_cli("re-ingest", "--rag-dir", str(self.rag_dir), "--key", "smith2023benchmark", "--yes")
        self.assertEqual(result.returncode, 0)
        updated = self.source_path.read_text(encoding="utf-8")
        self.assertIn(old_doi, updated)
        self.assertIn("Manual summary.", updated)

    def test_reingest_rejects_invalid_pdf(self):
        bad = self.tmp / "bad.pdf"
        bad.write_text("not a pdf", encoding="utf-8")
        result = self.run_cli(
            "re-ingest",
            "--rag-dir", str(self.rag_dir),
            "--key", "smith2023benchmark",
            "--replace-pdf", str(bad),
            "--dry-run",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid", result.stdout.lower())


def minimal_pdf_bytes():
    return b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


if __name__ == "__main__":
    unittest.main()
