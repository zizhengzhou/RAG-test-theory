"""Tests for Qdrant store dry-run planning."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from qdrant_store import build_upsert_plan, upsert_chunks


class TestQdrantStore(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.chunks = self.tmp / "chunks.jsonl"
        self.chunks.write_text(
            json.dumps({"chunk_id": "c1", "text": "alpha", "citation_key": "paper"}) + "\n"
            + json.dumps({"chunk_id": "c2", "text": "beta", "citation_key": "paper"}) + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_build_upsert_plan(self):
        plan = build_upsert_plan(self.chunks)

        self.assertEqual(plan.collection, "darw_evidence_chunks")
        self.assertEqual(plan.points, 2)
        self.assertEqual(plan.chunk_ids, ["c1", "c2"])

    def test_upsert_dry_run_has_no_dependency(self):
        plan = upsert_chunks(self.chunks, dry_run=True)

        self.assertTrue(plan.dry_run)
        self.assertEqual(plan.points, 2)


if __name__ == "__main__":
    unittest.main()
