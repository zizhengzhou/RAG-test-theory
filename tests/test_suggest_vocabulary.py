"""Tests for evidence-driven vocabulary suggestion."""

import sys
import tempfile
import unittest
from pathlib import Path

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

    def test_extract_candidate_terms_from_chunks(self):
        terms = extract_candidate_terms(self.rag_dir, citation_key="paper")
        labels = [item["term"].lower() for item in terms]
        self.assertTrue(any("superconducting resonator" in label for label in labels))

    def test_suggest_edges_uses_local_vocabulary(self):
        suggestions = suggest_edges(self.rag_dir, citation_key="paper", online=False)
        entries = suggestions.get("physical_systems", [])
        self.assertTrue(any(entry["canonical_id"] == "local:superconducting-resonator" for entry in entries))


if __name__ == "__main__":
    unittest.main()
