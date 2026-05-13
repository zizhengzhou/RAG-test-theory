"""Tests for applying source-page edge suggestions."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from apply_edges import apply_edge_plan, build_edge_plan
from common import ensure_rag_dirs, read_frontmatter


VOCAB = """# DARW Vocabulary

Schema version: `darw-vocabulary-v1`

```yaml
terms:
- canonical_id: local:superconducting-resonator
  label: Superconducting resonator
  namespace: local
  category: physical_systems
  aliases:
  - superconducting resonator
  - superconducting resonators
  parent: null
  related: []
  source: user
  needs_review: false
```
"""


class TestApplyEdges(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir)
        (self.rag_dir / "vocabulary.md").write_text(VOCAB, encoding="utf-8")
        source = self.rag_dir / "summary" / "sources" / "paper.md"
        source.write_text(
            "---\n"
            "schema_version: darw-source-v1\n"
            "citation_key: paper\n"
            "source:\n"
            "  title: Paper\n"
            "  abstract: ''\n"
            "edges:\n"
            "  research_areas: []\n"
            "  physical_systems: []\n"
            "  techniques: []\n"
            "  properties: []\n"
            "  models: []\n"
            "  observables: []\n"
            "  datasets: []\n"
            "  experiments: []\n"
            "---\n\n# Paper\n",
            encoding="utf-8",
        )
        chunk = {
            "chunk_id": "chunk-1",
            "doc_id": "doc",
            "citation_key": "paper",
            "section_title": "Detector",
            "text": "The superconducting resonator detector shows TLS noise.",
        }
        (self.rag_dir / "reference" / "chunks" / "doc.jsonl").write_text(json.dumps(chunk) + "\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_apply_edges_writes_vocabulary_backed_edges(self):
        plan = build_edge_plan(self.rag_dir, key="paper", online=False)
        self.assertEqual(plan.errors, [])
        self.assertTrue(any(item.canonical_id == "local:superconducting-resonator" for item in plan.new_items))

        added = apply_edge_plan(plan)

        self.assertGreaterEqual(added, 1)
        fm, _ = read_frontmatter(self.rag_dir / "summary" / "sources" / "paper.md")
        edges = fm["edges"]["physical_systems"]
        self.assertEqual(edges[0]["canonical_id"], "local:superconducting-resonator")
        self.assertIn("confidence", edges[0])

    def test_repeated_apply_preserves_existing_edges(self):
        first = build_edge_plan(self.rag_dir, key="paper", online=False)
        apply_edge_plan(first)
        second = build_edge_plan(self.rag_dir, key="paper", online=False)
        added = apply_edge_plan(second)

        self.assertEqual(added, 0)

    def test_missing_vocabulary_term_is_error(self):
        (self.rag_dir / "vocabulary.md").write_text(
            "# DARW Vocabulary\n\nSchema version: `darw-vocabulary-v1`\n\n```yaml\nterms: []\n```\n",
            encoding="utf-8",
        )

        plan = build_edge_plan(self.rag_dir, key="paper", online=False)

        self.assertTrue(plan.errors)

    def test_unresolved_suggestions_are_review_items_not_errors(self):
        plan = build_edge_plan(self.rag_dir, key="paper", online=False)

        unresolved = [item for item in plan.items if item.status == "unresolved"]
        self.assertTrue(unresolved)
        self.assertTrue(all(item.needs_review for item in unresolved))


if __name__ == "__main__":
    unittest.main()
