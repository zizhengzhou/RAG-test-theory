"""Tests for the plugin smoke test workflow."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from plugin_smoke_test import run_smoke_test


class TestPluginSmoke(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[1] / ".tmp_test_plugin_smoke"
        scratch.mkdir(exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(dir=scratch))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_smoke_test_produces_research_context(self):
        report = run_smoke_test(self.tmp, keep=True)

        self.assertTrue(report["success"])
        self.assertTrue(report["plugin_manifest_exists"])
        self.assertEqual(report["steps"]["bootstrap_apply"]["appended"], 1)
        self.assertGreater(report["steps"]["research_context"]["chunks"], 0)
        self.assertTrue(report["steps"]["research_context"]["first_chunk_id"])
        self.assertTrue(report["steps"]["research_context"]["has_trace"])


if __name__ == "__main__":
    unittest.main()
