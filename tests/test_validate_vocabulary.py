"""Tests for DARW vocabulary validation."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from common import ensure_rag_dirs, write_frontmatter
from validate_vocabulary import validate_vocabulary


VOCAB_SKELETON = """# DARW Vocabulary

Schema version: `darw-vocabulary-v1`

## Terms

```yaml
terms: []
```
"""

VOCAB_WITH_TERM = """# DARW Vocabulary

Schema version: `darw-vocabulary-v1`

## Terms

```yaml
terms:
  - canonical_id: "local:test-term"
    label: "Test Term"
    namespace: "local"
    category: "techniques"
    aliases: ["test-alias"]
    source: "user"
    needs_review: false
```
"""


class TestValidateVocabulary(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rag_dir = self.tmp / "RAG"
        ensure_rag_dirs(self.rag_dir, ())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_vocab(self, content: str) -> None:
        (self.rag_dir / "vocabulary.md").write_text(content, encoding="utf-8")

    def _write_source_page(self, key: str, edges: dict) -> None:
        fm = write_frontmatter({
            "schema_version": "darw-source-v1",
            "doc_id": f"arxiv:{key}",
            "citation_key": key,
            "identifiers": {"arxiv": key, "doi": None, "inspire": None, "zotero_key": None, "url": None},
            "source": {"title": "Test", "authors": [], "year": "2024", "venue": None, "abstract": "",
                       "source_type": "arxiv_source", "primary_evidence": "", "original_pdf": "",
                       "original_tex": None, "source_sha256": "", "parser": "", "parser_version": "", "parsed_at": ""},
            "edges": edges,
            "chunk_manifest": "",
            "quality": {"extraction_confidence": "low", "needs_human_review": True,
                        "math_extraction_quality": "unknown", "metadata_conflicts": []},
            "status": {"reading_status": "unread", "relevance": "unknown", "last_checked": ""},
        })
        (self.rag_dir / "summary" / "sources" / f"{key}.md").write_text(fm + "\n# Test\n", encoding="utf-8")

    def test_empty_terms_is_valid(self):
        self._write_vocab(VOCAB_SKELETON)
        issues = validate_vocabulary(self.rag_dir)
        self.assertEqual(len(issues), 0)

    def test_missing_schema_version_is_reported(self):
        content = VOCAB_SKELETON.replace("darw-vocabulary-v1", "darw-vocabulary-v9")
        self._write_vocab(content)
        issues = validate_vocabulary(self.rag_dir)
        self.assertTrue(any("schema version" in i for i in issues))

    def test_missing_yaml_block_is_reported(self):
        self._write_vocab("# No YAML here\n")
        issues = validate_vocabulary(self.rag_dir)
        self.assertTrue(any("YAML code block" in i for i in issues))

    def test_valid_term_has_no_issues(self):
        self._write_vocab(VOCAB_WITH_TERM)
        issues = validate_vocabulary(self.rag_dir)
        self.assertEqual(len(issues), 0)

    def test_term_missing_required_field_is_reported(self):
        # Build YAML without the 'label' field — cleaner than string surgery
        content = VOCAB_WITH_TERM.replace(
            "    label: \"Test Term\"\n",
            "",
        )
        self._write_vocab(content)
        issues = validate_vocabulary(self.rag_dir)
        self.assertTrue(any("missing required field" in i for i in issues))

    def test_unknown_category_is_reported(self):
        content = VOCAB_WITH_TERM.replace("category: \"techniques\"", "category: \"unknown_cat\"")
        self._write_vocab(content)
        issues = validate_vocabulary(self.rag_dir)
        self.assertTrue(any("unknown category" in i for i in issues))

    def test_duplicate_canonical_id_is_reported(self):
        content = VOCAB_WITH_TERM.replace("aliases: [\"test-alias\"]", "aliases: [\"test-alias\"]\n  - canonical_id: \"local:test-term\"\n    label: \"Duplicate\"\n    namespace: \"local\"\n    category: \"techniques\"\n    aliases: []\n    source: \"user\"\n    needs_review: false")
        self._write_vocab(content)
        issues = validate_vocabulary(self.rag_dir)
        self.assertTrue(any("duplicate" in i for i in issues))

    def test_alias_namespace_is_reported(self):
        content = VOCAB_WITH_TERM.replace("namespace: \"local\"", "namespace: \"alias:\"")
        self._write_vocab(content)
        issues = validate_vocabulary(self.rag_dir)
        self.assertTrue(any("alias" in i.lower() and "namespace" in i.lower() for i in issues))

    def test_alias_used_as_edge_canonical_id_is_reported(self):
        self._write_vocab(VOCAB_WITH_TERM)
        self._write_source_page("testkey", {
            "techniques": [{"canonical_id": "test-alias", "label": "Test Alias"}],
            "research_areas": [],
            "physical_systems": [],
            "properties": [],
            "models": [],
            "observables": [],
            "datasets": [],
            "experiments": [],
        })
        issues = validate_vocabulary(self.rag_dir)
        self.assertTrue(any("alias" in i and "test-alias" in i for i in issues))


if __name__ == "__main__":
    unittest.main()
