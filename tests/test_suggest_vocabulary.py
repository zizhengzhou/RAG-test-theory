"""Tests for evidence-driven vocabulary suggestion."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from common import ensure_rag_dirs
from suggest_vocabulary import extract_candidate_terms, suggest_edges


VOCAB = """# DARW Vocabulary

Schema version: `darw-vocabulary-v1`

```yaml
terms:
  - canonical_id: "local:superconducting-resonator"
    label: "Superconducting resonator"
    namespace: "local"
    category: "physical_systems"
    aliases: ["superconducting resonator", "superconducting resonators"]
    source: "user"
    needs_review: false
```
"""


class TestSuggestVocabulary(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir, ())
        (self.rag_dir / "vocabulary.md").write_text(VOCAB, encoding="utf-8")
        chunk = {
            "chunk_id": "chunk-1",
            "doc_id": "doc",
            "citation_key": "paper",
            "section_title": "Detector",
            "text": "The superconducting resonator detector shows TLS noise in the experiment.",
        }
        (self.rag_dir / "reference" / "chunks" / "doc.jsonl").write_text(
            __import__("json").dumps(chunk) + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_chunk(self, key, text, section_title="Results"):
        chunk = {
            "chunk_id": f"chunk-{key}",
            "doc_id": "doc",
            "citation_key": key,
            "section_title": section_title,
            "text": text,
        }
        (self.rag_dir / "reference" / "chunks" / f"{key}.jsonl").write_text(
            json.dumps(chunk) + "\n",
            encoding="utf-8",
        )

    def test_extract_candidate_terms_from_chunks(self):
        terms = extract_candidate_terms(self.rag_dir, citation_key="paper")
        labels = [item["term"].lower() for item in terms]
        self.assertTrue(any("superconducting resonator" in label for label in labels))

    def test_suggest_edges_uses_local_vocabulary(self):
        suggestions = suggest_edges(self.rag_dir, citation_key="paper", online=False)
        entries = suggestions.get("physical_systems", [])
        self.assertTrue(any(entry["canonical_id"] == "local:superconducting-resonator" for entry in entries))

    def test_trims_generic_trailing_container_words(self):
        terms = extract_candidate_terms(self.rag_dir, citation_key="paper")
        labels = {item["term"].lower() for item in terms}

        self.assertIn("superconducting resonator", labels)
        self.assertNotIn("superconducting resonator detector", labels)

    def test_loads_bom_prefixed_jsonl_chunks(self):
        chunk = {
            "chunk_id": "chunk-bom",
            "doc_id": "doc",
            "citation_key": "bom",
            "section_title": "Detector",
            "text": "The superconducting resonator appears again.",
        }
        (self.rag_dir / "reference" / "chunks" / "bom.jsonl").write_text(
            "\ufeff" + __import__("json").dumps(chunk) + "\n",
            encoding="utf-8",
        )

        terms = extract_candidate_terms(self.rag_dir, citation_key="bom")

        self.assertTrue(any("superconducting" in item["term"].lower() for item in terms))

    def test_filters_common_pdf_reference_noise(self):
        chunk = {
            "chunk_id": "chunk-noise",
            "doc_id": "doc",
            "citation_key": "noise",
            "section_title": "References",
            "text": (
                "Article Phys Lett July which there intentionally omitted picture. "
                "Coherent elastic neutrino-nucleus scattering is measured near a reactor. "
                "Coherent elastic neutrino-nucleus scattering constrains neutrinos."
            ),
        }
        (self.rag_dir / "reference" / "chunks" / "noise.jsonl").write_text(
            json.dumps(chunk) + "\n",
            encoding="utf-8",
        )

        terms = extract_candidate_terms(self.rag_dir, citation_key="noise", limit=20)
        labels = {item["term"].lower() for item in terms}

        self.assertNotIn("article", labels)
        self.assertNotIn("phys", labels)
        self.assertNotIn("july", labels)
        self.assertTrue(any("neutrino-nucleus scattering" in label for label in labels))

    def test_suppresses_broad_fragments_when_specific_phrases_exist(self):
        self.write_chunk(
            "fragments",
            " ".join(
                [
                    "The reactor detector program studies coherent elastic neutrino-nucleus scattering.",
                    "Coherent elastic neutrino-nucleus scattering near a reactor uses a cryogenic detector threshold.",
                    "The detector response and reactor flux are monitored during the physics run.",
                ]
            ),
        )

        terms = extract_candidate_terms(self.rag_dir, citation_key="fragments", limit=30)
        labels = {item["term"].lower() for item in terms}

        self.assertNotIn("reactor", labels)
        self.assertNotIn("detector", labels)
        self.assertNotIn("coherent elastic", labels)
        self.assertTrue(any("coherent elastic neutrino-nucleus scattering" in label for label in labels))
        self.assertTrue(any("cryogenic detector threshold" in label for label in labels))

    def test_longer_phrase_dominates_shorter_prefix(self):
        self.write_chunk(
            "prefix",
            "Coherent elastic measurements motivate coherent elastic neutrino-nucleus scattering. "
            "Coherent elastic neutrino-nucleus scattering is the reviewed terminology.",
        )

        terms = extract_candidate_terms(self.rag_dir, citation_key="prefix", limit=20)
        labels = [item["term"].lower() for item in terms]

        self.assertIn("coherent elastic neutrino-nucleus scattering", labels)
        self.assertNotIn("coherent elastic", labels)
        self.assertNotIn("coherent elastic neutrino-nucleus", labels)
        self.assertNotIn("elastic neutrino-nucleus", labels)

    def test_preserves_mixed_case_acronym_terms(self):
        self.write_chunk(
            "acronyms",
            "CEvNS is measured by CONUS and CRESST. "
            "CEvNS signatures constrain TLS noise in cryogenic detectors.",
        )

        terms = extract_candidate_terms(self.rag_dir, citation_key="acronyms", limit=20)
        labels = {item["term"] for item in terms}

        self.assertIn("CEvNS", labels)
        self.assertIn("CONUS", labels)
        self.assertIn("CRESST", labels)

    def test_existing_local_vocabulary_alias_is_protected_from_fragment_suppression(self):
        self.write_chunk(
            "alias",
            "Detector thresholds are important. Detector thresholds improve detector background rejection.",
        )
        (self.rag_dir / "vocabulary.md").write_text(
            """# DARW Vocabulary

Schema version: `darw-vocabulary-v1`

```yaml
terms:
- canonical_id: local:detector-thresholds
  label: Detector thresholds
  namespace: local
  category: properties
  aliases:
  - detector thresholds
  parent: null
  related: []
  source: user
  needs_review: false
```
""",
            encoding="utf-8",
        )

        suggestions = suggest_edges(self.rag_dir, citation_key="alias", online=False)
        entries = suggestions.get("properties", [])

        self.assertTrue(any(entry["canonical_id"] == "local:detector-thresholds" for entry in entries))

    @patch("physh_mapper.query_concept")
    @patch("physh_mapper.search_concepts")
    def test_online_suggestions_can_resolve_to_physh_terms(self, search_concepts, query_concept):
        (self.rag_dir / "vocabulary.md").write_text(
            """# DARW Vocabulary

Schema version: `darw-vocabulary-v1`

```yaml
terms: []
```
""",
            encoding="utf-8",
        )
        chunk = {
            "chunk_id": "chunk-physh",
            "doc_id": "doc",
            "citation_key": "physh-paper",
            "section_title": "Materials",
            "text": "Graphene.",
        }
        chunk_2 = {
            "chunk_id": "chunk-physh-2",
            "doc_id": "doc",
            "citation_key": "physh-paper",
            "section_title": "Materials",
            "text": "Graphene.",
        }
        (self.rag_dir / "reference" / "chunks" / "physh.jsonl").write_text(
            __import__("json").dumps(chunk) + "\n" + __import__("json").dumps(chunk_2) + "\n",
            encoding="utf-8",
        )
        search_concepts.return_value = [
            {
                "id": "abc123",
                "label": "graphene",
            }
        ]
        query_concept.return_value = {
            "id": "abc123",
            "label": "Graphene",
            "facets": [{"label": "Physical Systems"}],
        }

        suggestions = suggest_edges(self.rag_dir, citation_key="physh-paper", online=True)
        entries = suggestions.get("physical_systems", [])

        self.assertTrue(any(entry["canonical_id"] == "physh:abc123" for entry in entries))


if __name__ == "__main__":
    unittest.main()
