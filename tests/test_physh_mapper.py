"""Tests for PhySH vocabulary resolution."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from common import ensure_rag_dirs
from physh_mapper import _candidate_match_score, resolve_term


VOCAB_EMPTY = """# DARW Vocabulary

Schema version: `darw-vocabulary-v1`

```yaml
terms: []
```
"""


class TestPhyshMapper(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir)
        (self.rag_dir / "vocabulary.md").write_text(VOCAB_EMPTY, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @patch("physh_mapper.query_concept")
    @patch("physh_mapper.search_concepts")
    def test_online_exact_match_resolves_to_physh_entity(self, search_concepts, query_concept):
        search_concepts.return_value = [
            {
                "id": "abc123",
                "label": "Superconducting resonators",
            }
        ]
        query_concept.return_value = {
            "id": "abc123",
            "label": "Superconducting resonators",
            "facets": [{"label": "Physical Systems"}],
        }

        entity = resolve_term(
            "Superconducting resonators",
            self.rag_dir / "vocabulary.md",
            self.rag_dir / "reference",
            online=True,
        )

        self.assertEqual(entity.canonical_id, "physh:abc123")
        self.assertEqual(entity.namespace, "physh")
        self.assertEqual(entity.category, "physical_systems")
        self.assertEqual(entity.source, "physh_api")
        self.assertFalse(entity.needs_review)
        self.assertEqual(entity.match_type, "exact")
        self.assertEqual(entity.match_score, 1.0)

    @patch("physh_mapper.search_concepts")
    def test_offline_unmatched_term_stays_local_review_candidate(self, search_concepts):
        entity = resolve_term(
            "Superconducting resonators",
            self.rag_dir / "vocabulary.md",
            self.rag_dir / "reference",
            online=False,
        )

        self.assertEqual(entity.canonical_id, "local:superconducting-resonators")
        self.assertEqual(entity.namespace, "local")
        self.assertEqual(entity.source, "unresolved")
        self.assertTrue(entity.needs_review)
        search_concepts.assert_not_called()

    @patch("physh_mapper.query_concept")
    @patch("physh_mapper.search_concepts")
    def test_online_reranks_safe_phrase_extension_over_search_order(self, search_concepts, query_concept):
        search_concepts.return_value = [
            {
                "id": "bad-match",
                "label": "Deep inelastic scattering",
                "facets": [{"label": "Research Areas"}],
            },
            {
                "id": "good-match",
                "label": "Elastic scattering reactions",
                "facets": [{"label": "Research Areas"}],
            }
        ]

        entity = resolve_term(
            "elastic scattering",
            self.rag_dir / "vocabulary.md",
            self.rag_dir / "reference",
            online=True,
        )

        self.assertEqual(entity.canonical_id, "physh:good-match")
        self.assertEqual(entity.label, "Elastic scattering reactions")
        self.assertEqual(entity.namespace, "physh")
        self.assertEqual(entity.source, "physh_api")
        self.assertTrue(entity.needs_review)
        self.assertEqual(entity.match_type, "semantic")
        self.assertGreaterEqual(entity.match_score, 0.84)
        query_concept.assert_not_called()

    @patch("physh_mapper.query_concept")
    @patch("physh_mapper.search_concepts")
    def test_online_weak_single_word_expansion_is_not_auto_accepted(self, search_concepts, query_concept):
        search_concepts.return_value = [
            {
                "id": "too-broad",
                "label": "Total cross sections",
                "facets": [{"label": "Observables"}],
            }
        ]

        entity = resolve_term(
            "cross section",
            self.rag_dir / "vocabulary.md",
            self.rag_dir / "reference",
            online=True,
        )

        self.assertEqual(entity.canonical_id, "local:cross-section")
        self.assertEqual(entity.namespace, "local")
        self.assertEqual(entity.source, "unresolved")
        self.assertTrue(entity.needs_review)
        query_concept.assert_not_called()

    def test_candidate_match_score_penalizes_dangerous_inelastic_mismatch(self):
        good = _candidate_match_score("elastic scattering", "Elastic scattering reactions")
        bad = _candidate_match_score("elastic scattering", "Deep inelastic scattering")

        self.assertGreaterEqual(good, 0.84)
        self.assertEqual(bad, 0.0)


if __name__ == "__main__":
    unittest.main()
