"""Tests for applying vocabulary suggestions."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from apply_vocabulary import apply_vocabulary_plan, build_vocabulary_plan
from common import ensure_rag_dirs
from physh_mapper import load_vocabulary_terms


VOCAB_EMPTY = """# DARW Vocabulary

Schema version: `darw-vocabulary-v1`

```yaml
terms: []
```
"""


class TestApplyVocabulary(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir)
        (self.rag_dir / "vocabulary.md").write_text(VOCAB_EMPTY, encoding="utf-8")
        chunk = {
            "chunk_id": "chunk-1",
            "doc_id": "doc",
            "citation_key": "paper",
            "section_title": "Detector",
            "text": "The superconducting resonator detector shows TLS noise in the experiment.",
        }
        (self.rag_dir / "reference" / "chunks" / "doc.jsonl").write_text(json.dumps(chunk) + "\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_empty_terms_default_does_not_append_local_terms(self):
        plan = build_vocabulary_plan(self.rag_dir, key="paper", online=False)
        self.assertGreaterEqual(len(plan.new_terms), 1)

        added = apply_vocabulary_plan(plan)

        self.assertEqual(added, 0)
        terms = load_vocabulary_terms(self.rag_dir / "vocabulary.md")
        self.assertEqual(terms, [])

    def test_accepted_local_terms_are_appended(self):
        review_plan = build_vocabulary_plan(self.rag_dir, key="paper", online=False)
        local_id = next(term.canonical_id for term in review_plan.new_terms if term.canonical_id.startswith("local:"))
        plan = build_vocabulary_plan(self.rag_dir, key="paper", online=False, accepted={local_id})
        added = apply_vocabulary_plan(plan)

        self.assertEqual(added, 1)
        terms = load_vocabulary_terms(self.rag_dir / "vocabulary.md")
        ids = {term["canonical_id"] for term in terms}
        self.assertIn(local_id, ids)

    def test_repeated_apply_does_not_duplicate_terms(self):
        plan = build_vocabulary_plan(self.rag_dir, key="paper", online=False)
        first = apply_vocabulary_plan(plan)
        second_plan = build_vocabulary_plan(self.rag_dir, key="paper", online=False)
        second = apply_vocabulary_plan(second_plan)

        self.assertEqual(first, 0)
        self.assertEqual(second, 0)

    def test_existing_terms_are_reported_as_existing(self):
        (self.rag_dir / "vocabulary.md").write_text(
            """# DARW Vocabulary

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
""",
            encoding="utf-8",
        )

        plan = build_vocabulary_plan(self.rag_dir, key="paper", online=False)

        self.assertTrue(any(term.status == "existing" for term in plan.terms))

    @patch("apply_vocabulary.suggest_edges")
    def test_new_physh_terms_auto_apply_without_accept(self, suggest_edges):
        suggest_edges.return_value = {
            "physical_systems": [
                {
                    "canonical_id": "physh:abc123",
                    "label": "Superconducting resonators",
                    "local_aliases": ["resonators"],
                    "confidence": 1.0,
                    "needs_review": False,
                }
            ]
        }

        plan = build_vocabulary_plan(self.rag_dir, key="paper", online=True)
        self.assertTrue(plan.new_terms[0].auto_apply)
        added = apply_vocabulary_plan(plan)

        self.assertEqual(added, 1)
        ids = {term["canonical_id"] for term in load_vocabulary_terms(self.rag_dir / "vocabulary.md")}
        self.assertIn("physh:abc123", ids)

    @patch("apply_vocabulary.suggest_edges")
    def test_review_physh_candidates_require_accept(self, suggest_edges):
        suggest_edges.return_value = {
            "research_areas": [
                {
                    "canonical_id": "physh:semantic123",
                    "label": "Elastic scattering reactions",
                    "local_aliases": ["elastic scattering"],
                    "confidence": 0.91,
                    "needs_review": True,
                }
            ]
        }

        review_plan = build_vocabulary_plan(self.rag_dir, key="paper", online=True)
        self.assertFalse(review_plan.new_terms[0].auto_apply)
        self.assertTrue(review_plan.new_terms[0].needs_review)
        self.assertEqual(apply_vocabulary_plan(review_plan), 0)

        accept_plan = build_vocabulary_plan(self.rag_dir, key="paper", online=True, accepted={"physh:semantic123"})
        self.assertTrue(accept_plan.new_terms[0].auto_apply)
        self.assertEqual(apply_vocabulary_plan(accept_plan), 1)
        term = load_vocabulary_terms(self.rag_dir / "vocabulary.md")[0]
        self.assertEqual(term["canonical_id"], "physh:semantic123")
        self.assertEqual(term["label"], "Elastic scattering reactions")
        self.assertEqual(term["aliases"], ["elastic scattering"])


if __name__ == "__main__":
    unittest.main()
