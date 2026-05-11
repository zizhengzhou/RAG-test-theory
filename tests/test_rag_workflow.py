"""End-to-end RAG workflow test."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))
from common import ensure_rag_dirs, append_log
from bib_parser import parse_bibtex_file, render_bibtex
from dedup import deduplicate_entries
from pdf_validator import is_pdf
from ingest import default_frontmatter

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestRAGWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_init_creates_directory_structure(self):
        ensure_rag_dirs(self.rag_dir, ["methods", "models"])
        required = [
            "summary/sources",
            "summary/synthesis",
            "summary/methods",
            "summary/models",
            "reference/pdfs",
            "reference/imports",
        ]
        for path in required:
            self.assertTrue((self.rag_dir / path).is_dir(), f"missing {path}")

    def test_init_creates_rag_files(self):
        from rag_init import main as rag_init_main
        import io
        import contextlib

        # Use temporary to avoid mutating real RAG
        import subprocess
        import shutil
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "rag" / "rag_init.py"),
                "--rag-dir", str(self.rag_dir),
                "--dimensions", "methods,models",
                "--template-fields", "summary,key findings",
                "--vocabulary", "methods",
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(result.returncode, 0)
        for file in ["SKILL.md", "index.md", "template.md", "vocabulary.md", "log.md"]:
            self.assertTrue((self.rag_dir / file).exists(), f"missing {file}")

    def test_bib_import_then_ingest_then_query(self):
        # Setup a minimal RAG init
        import subprocess
        init_result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "rag" / "rag_init.py"),
                "--rag-dir", str(self.rag_dir),
                "--dimensions", "methods,models",
                "--template-fields", "summary,key findings",
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(init_result.returncode, 0)

        # import-bib
        import_result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "rag" / "import_bib.py"),
                "--bib", str(FIXTURES / "sample.bib"),
                "--rag-dir", str(self.rag_dir),
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(import_result.returncode, 0)
        self.assertIn("new entries: 3", import_result.stdout.lower())
        self.assertTrue((self.rag_dir / "references.bib").exists())

        # validate references.bib content
        entries = parse_bibtex_file(self.rag_dir / "references.bib")
        self.assertEqual(len(entries), 3)

        # ingest
        ingest_result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "rag" / "ingest.py"),
                "--rag-dir", str(self.rag_dir),
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(ingest_result.returncode, 0)
        self.assertTrue((self.rag_dir / "summary" / "sources" / "smith2023benchmark.md").exists())
        self.assertTrue((self.rag_dir / "summary" / "sources" / "chen2024improved.md").exists())
        self.assertTrue((self.rag_dir / "summary" / "sources" / "lee2024survey.md").exists())

        # update-index
        idx_result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "rag" / "update_index.py"),
                "--rag-dir", str(self.rag_dir),
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(idx_result.returncode, 0)

        # query
        query_result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "rag" / "query.py"),
                "--rag-dir", str(self.rag_dir),
                "--query", "coupled-channel",
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(query_result.returncode, 0)
        self.assertIn("chen2024improved", query_result.stdout)

        # sync-from-notes
        sync_result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "rag" / "sync_from_notes.py"),
                "--rag-dir", str(self.rag_dir),
                "--notes-dir", str(FIXTURES / "notes"),
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(sync_result.returncode, 0)
        sync_path = self.rag_dir / "summary" / "synthesis" / "notes-sync.md"
        self.assertTrue(sync_path.exists())
        content = sync_path.read_text(encoding="utf-8")
        self.assertIn("CDCC", content)

        # lint
        lint_result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "rag" / "rag_lint.py"),
                "--rag-dir", str(self.rag_dir),
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        # lint should run; exit 1 is normal when issues are found
        self.assertIn(lint_result.returncode, (0, 1),
            f"lint crashed: code={lint_result.returncode} stderr={lint_result.stderr}")

        # verify log was written
        self.assertTrue((self.rag_dir / "log.md").exists())
        log_content = (self.rag_dir / "log.md").read_text()
        self.assertIn("rag-init", log_content)

    def test_import_bib_dry_run_has_no_side_effects(self):
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "rag" / "import_bib.py"),
                "--bib", str(FIXTURES / "sample.bib"),
                "--rag-dir", str(self.rag_dir),
                "--dry-run",
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("[dry-run] no files written", result.stdout)
        self.assertFalse((self.rag_dir / "references.bib").exists())
        self.assertFalse((self.rag_dir / "log.md").exists())

    def test_update_index_ignores_non_dimension_lists(self):
        import subprocess

        init_result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "rag" / "rag_init.py"),
                "--rag-dir", str(self.rag_dir),
                "--dimensions", "methods",
                "--vocabulary", "methods",
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(init_result.returncode, 0)
        source_dir = self.rag_dir / "summary" / "sources"
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "paper.md").write_text(
            "---\ntype: source\ncreated: 2025-01-01\ntitle: T\nauthors: [Alice, Bob]\nmethods: [uncategorized]\n---\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "rag" / "update_index.py"),
                "--rag-dir", str(self.rag_dir),
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(result.returncode, 0)
        self.assertTrue((self.rag_dir / "summary" / "methods" / "uncategorized.md").exists())
        self.assertFalse((self.rag_dir / "summary" / "authors").exists())

    def test_zip_importer_dry_run(self):
        import subprocess

        # Use fixture zip
        zip_path = FIXTURES / "zotero-rdf-minimal.zip"
        self.assertTrue(zip_path.exists(), "zotero-rdf-minimal.zip fixture missing")

        # Create references.bib first so import-zip can append
        (self.rag_dir / "references.bib").parent.mkdir(parents=True, exist_ok=True)
        (self.rag_dir / "references.bib").write_text("")

        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "rag" / "zip_importer.py"),
                "--zip", str(zip_path),
                "--rag-dir", str(self.rag_dir),
                "--dry-run",
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(result.returncode, 0, f"zip_importer failed: stdout={result.stdout[:300]} stderr={result.stderr[:300]}")
        self.assertIn("skip non-PDF", result.stdout)
        self.assertFalse((self.rag_dir / "reference").exists())
        self.assertFalse((self.rag_dir / "log.md").exists())


if __name__ == "__main__":
    unittest.main()
