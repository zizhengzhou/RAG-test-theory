"""Tests for vocabulary-backed wiki page generation."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from apply_edges import apply_edge_plan, build_edge_plan
from apply_vocabulary import apply_vocabulary_plan, build_vocabulary_plan
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

VOCAB_EMPTY = """# DARW Vocabulary

Schema version: `darw-vocabulary-v1`

```yaml
terms: []
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

    @patch("apply_edges.suggest_edges")
    @patch("apply_vocabulary.suggest_edges")
    def test_accepted_vocabulary_terms_drive_edges_and_wiki_without_manual_yaml(self, vocabulary_suggest_edges, edge_suggest_edges):
        suggestions = {
            "research_areas": [
                {
                    "canonical_id": "physh:semantic123",
                    "label": "Elastic scattering reactions",
                    "local_aliases": ["coherent elastic neutrino-nucleus scattering"],
                    "confidence": 0.91,
                    "needs_review": True,
                }
            ],
            "techniques": [
                {
                    "canonical_id": "local:pulse-shape-discrimination",
                    "label": "Pulse-shape discrimination",
                    "local_aliases": ["pulse-shape discrimination"],
                    "confidence": 0.0,
                    "needs_review": True,
                }
            ],
        }
        vocabulary_suggest_edges.return_value = suggestions
        edge_suggest_edges.return_value = suggestions
        (self.rag_dir / "vocabulary.md").write_text(VOCAB_EMPTY, encoding="utf-8")
        empty_edges = {category: [] for category in EDGE_CATEGORIES}
        fm = {
            "schema_version": "darw-source-v1",
            "doc_id": "arxiv:2601.00001",
            "citation_key": "paper",
            "source": {"title": "Paper"},
            "edges": empty_edges,
        }
        (self.rag_dir / "summary" / "sources" / "paper.md").write_text(write_frontmatter(fm) + "# Paper\n", encoding="utf-8")

        review_plan = build_vocabulary_plan(self.rag_dir, key="paper", online=True)
        self.assertEqual(apply_vocabulary_plan(review_plan), 0)

        accepted = {"physh:semantic123", "local:pulse-shape-discrimination"}
        accept_plan = build_vocabulary_plan(self.rag_dir, key="paper", online=True, accepted=accepted)
        self.assertEqual(apply_vocabulary_plan(accept_plan), 2)

        edge_plan = build_edge_plan(self.rag_dir, key="paper", online=True)
        self.assertEqual(edge_plan.errors, [])
        self.assertEqual({item.canonical_id for item in edge_plan.new_items}, accepted)
        self.assertEqual(apply_edge_plan(edge_plan), 2)

        source_fm, _ = read_frontmatter(self.rag_dir / "summary" / "sources" / "paper.md")
        self.assertEqual(source_fm["edges"]["research_areas"][0]["canonical_id"], "physh:semantic123")
        self.assertTrue(source_fm["edges"]["research_areas"][0]["needs_review"])
        self.assertEqual(source_fm["edges"]["techniques"][0]["canonical_id"], "local:pulse-shape-discrimination")

        wiki_plan = build_vocabulary_wiki_plan(self.rag_dir)
        self.assertEqual({node.canonical_id for node in wiki_plan.nodes}, accepted)
        self.assertEqual(apply_vocabulary_wiki_plan(wiki_plan), 2)
        physh_page = self.rag_dir / "summary" / "research_areas" / "physh_semantic123.md"
        local_page = self.rag_dir / "summary" / "techniques" / "local_pulse-shape-discrimination.md"
        self.assertTrue(physh_page.exists())
        self.assertTrue(local_page.exists())
        physh_fm, physh_body = read_frontmatter(physh_page)
        self.assertEqual(physh_fm["namespace"], "physh")
        self.assertEqual(physh_fm["canonical_id"], "physh:semantic123")
        self.assertIn("[[../sources/paper]]", physh_body)

        strict_plan = build_vocabulary_wiki_plan(self.rag_dir, strict_physh=True)
        self.assertEqual([node.canonical_id for node in strict_plan.nodes], ["physh:semantic123"])
        self.assertEqual(strict_plan.skipped[0]["canonical_id"], "local:pulse-shape-discrimination")


if __name__ == "__main__":
    unittest.main()
