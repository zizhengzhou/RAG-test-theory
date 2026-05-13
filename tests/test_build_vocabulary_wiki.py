"""Tests for vocabulary-backed wiki page generation."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from build_vocabulary_wiki import apply_vocabulary_wiki_plan, build_vocabulary_wiki_plan
from common import ensure_rag_dirs, read_frontmatter, write_frontmatter
from darw_schema import EDGE_CATEGORIES


VOCAB = """# DARW Vocabulary

Schema version: `darw-vocabulary-v1`

```yaml
terms:
- canonical_id: physh:abc123
  label: Superconducting resonators
  namespace: physh
  category: physical_systems
  aliases:
  - resonators
  parent: null
  related: []
  source: physh
  needs_review: false
- canonical_id: local:test
  label: Local Test
  namespace: local
  category: techniques
  aliases: []
  parent: null
  related: []
  source: user
  needs_review: true
```
"""


class TestBuildVocabularyWiki(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir)
        (self.rag_dir / "vocabulary.md").write_text(VOCAB, encoding="utf-8")
        edges = {category: [] for category in EDGE_CATEGORIES}
        edges["physical_systems"] = [{"canonical_id": "physh:abc123", "label": "Superconducting resonators"}]
        edges["techniques"] = [{"canonical_id": "local:test", "label": "Local Test"}]
        fm = {
            "schema_version": "darw-source-v1",
            "doc_id": "arxiv:2401.12345",
            "citation_key": "paper",
            "source": {"title": "Paper"},
            "edges": edges,
        }
        (self.rag_dir / "summary" / "sources" / "paper.md").write_text(write_frontmatter(fm) + "# Paper\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_plan_contains_physh_and_local_vocabulary_nodes(self):
        plan = build_vocabulary_wiki_plan(self.rag_dir)

        self.assertEqual([node.canonical_id for node in plan.nodes], ["local:test", "physh:abc123"])
        namespaces = {node.canonical_id: node.namespace for node in plan.nodes}
        self.assertEqual(namespaces["physh:abc123"], "physh")
        self.assertEqual(namespaces["local:test"], "local")
        self.assertEqual(plan.skipped, [])

    def test_apply_writes_vocabulary_node_pages(self):
        plan = build_vocabulary_wiki_plan(self.rag_dir)
        written = apply_vocabulary_wiki_plan(plan)

        self.assertEqual(written, 2)
        page = self.rag_dir / "summary" / "physical_systems" / "physh_abc123.md"
        local_page = self.rag_dir / "summary" / "techniques" / "local_test.md"
        self.assertTrue(page.exists())
        self.assertTrue(local_page.exists())
        fm, body = read_frontmatter(page)
        self.assertEqual(fm["canonical_id"], "physh:abc123")
        self.assertEqual(fm["namespace"], "physh")
        self.assertIn("[[../sources/paper]]", body)

        local_fm, local_body = read_frontmatter(local_page)
        self.assertEqual(local_fm["canonical_id"], "local:test")
        self.assertEqual(local_fm["namespace"], "local")
        self.assertIn("[[../sources/paper]]", local_body)

    def test_strict_physh_filters_local_nodes(self):
        plan = build_vocabulary_wiki_plan(self.rag_dir, strict_physh=True)

        self.assertEqual([node.canonical_id for node in plan.nodes], ["physh:abc123"])
        self.assertEqual(plan.skipped[0]["canonical_id"], "local:test")
        self.assertEqual(plan.skipped[0]["reason"], "strict-physh filter")


if __name__ == "__main__":
    unittest.main()
