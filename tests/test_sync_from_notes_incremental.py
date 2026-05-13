"""Tests for incremental notes sync."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from common import ensure_rag_dirs
from sync_from_notes import extract_from_note, sync_notes


class TestSyncFromNotesIncremental(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        self.notes_dir = self.tmp / "notes"
        ensure_rag_dirs(self.rag_dir)
        self.notes_dir.mkdir()
        (self.notes_dir / "note.md").write_text(
            "# Run 1\n\n"
            "- Finding: CDCC works for breakup [@chen2024]\n"
            "- Method: Use coupled-channel analysis\n"
            "- Failed: PDF extraction missed equations\n"
            "- Decision: Keep chunk provenance\n",
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_extract_records_line_and_heading(self):
        items = extract_from_note(self.notes_dir / "note.md", self.rag_dir)

        self.assertEqual(items[0]["heading"], "Run 1")
        self.assertEqual(items[0]["line"], 3)
        self.assertEqual(items[0]["bucket"], "claims")

    def test_sync_is_incremental_and_grouped(self):
        out, first_new = sync_notes(self.rag_dir, self.notes_dir)
        _, second_new = sync_notes(self.rag_dir, self.notes_dir)
        text = out.read_text(encoding="utf-8")

        self.assertEqual(first_new, 4)
        self.assertEqual(second_new, 0)
        self.assertIn("## Claims", text)
        self.assertIn("## Methods", text)
        self.assertIn("## Failures", text)
        self.assertIn("## Decisions", text)
        self.assertEqual(text.count("<!-- note:"), 4)


if __name__ == "__main__":
    unittest.main()
