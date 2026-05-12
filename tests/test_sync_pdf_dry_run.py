"""Tests for sync-pdf dry-run behavior."""

import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestSyncPdfDryRun(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        self.rag_dir.mkdir()
        self.source_pdf = self.tmp / "source.pdf"
        self.source_pdf.write_bytes(minimal_pdf_bytes())
        self.references = self.rag_dir / "references.bib"
        self.references.write_text(
            "\n".join(
                [
                    "@article{paper2026,",
                    "  title = {Paper With Local PDF},",
                    "  author = {Doe, Jane},",
                    "  year = {2026},",
                    f"  file = {{{self.source_pdf}}},",
                    "}",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_sync_pdf(self, *args):
        return subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "rag" / "sync_pdf.py"),
                *args,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_dry_run_does_not_create_target_directory_or_log(self):
        before_hash = sha256(self.references)

        result = self.run_sync_pdf("--rag-dir", str(self.rag_dir), "--dry-run")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("would create directory", result.stdout)
        self.assertIn("would copy", result.stdout)
        self.assertIn("would append log entry", result.stdout)
        self.assertFalse((self.rag_dir / "reference" / "pdfs").exists())
        self.assertFalse((self.rag_dir / "log.md").exists())
        self.assertEqual(sha256(self.references), before_hash)

    def test_dry_run_does_not_change_existing_log_or_manifest(self):
        log = self.rag_dir / "log.md"
        log.write_text("existing log\n", encoding="utf-8")
        before_log_hash = sha256(log)
        before_references_hash = sha256(self.references)

        result = self.run_sync_pdf("--rag-dir", str(self.rag_dir), "--dry-run")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sha256(log), before_log_hash)
        self.assertEqual(sha256(self.references), before_references_hash)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def minimal_pdf_bytes():
    return b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


if __name__ == "__main__":
    unittest.main()
