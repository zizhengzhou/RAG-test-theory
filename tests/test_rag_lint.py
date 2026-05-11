"""Tests for rag_lint."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))
from rag_lint import check_bibtex_manifest, check_dead_links, check_source_fm, check_pdf_refs, check_auto_blocks, load_vocabulary

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def make_rag_dir() -> Path:
    tmp = Path(tempfile.mkdtemp())
    (tmp / "summary" / "sources").mkdir(parents=True)
    (tmp / "summary" / "synthesis").mkdir(parents=True)
    (tmp / "summary" / "methods").mkdir(parents=True)
    (tmp / "reference" / "pdfs").mkdir(parents=True)
    (tmp / "vocabulary.md").write_text("# vocab\n")
    (tmp / "references.bib").write_text("@article{key1, title = {Test}}")
    return tmp


class TestLint(unittest.TestCase):
    def test_no_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as td:
            rag_dir = Path(td)
            (rag_dir / "references.bib").write_text(
                "@article{a,title={T1}}\n@article{b,title={T2}}\n"
            )
            issues = check_bibtex_manifest(rag_dir)
            self.assertEqual(issues, [])

    def test_duplicate_key_detected(self):
        with tempfile.TemporaryDirectory() as td:
            rag_dir = Path(td)
            (rag_dir / "references.bib").write_text(
                "@article{a,title={T1}}\n@article{a,title={T2}}\n"
            )
            issues = check_bibtex_manifest(rag_dir)
            self.assertTrue(any("duplicate" in i.lower() for i in issues))

    def test_dead_link_detected(self):
        with tempfile.TemporaryDirectory() as td:
            rag_dir = Path(td)
            (rag_dir / "summary" / "sources").mkdir(parents=True)
            (rag_dir / "summary" / "sources" / "test.md").write_text(
                "[bad link](nonexistent.md)\n"
            )
            issues = check_dead_links(rag_dir)
            self.assertTrue(any("dead link" in i.lower() for i in issues))

    def test_relative_link_resolves_from_current_file(self):
        with tempfile.TemporaryDirectory() as td:
            rag_dir = Path(td)
            (rag_dir / "summary" / "sources").mkdir(parents=True)
            (rag_dir / "summary" / "reference").mkdir(parents=True)
            (rag_dir / "summary" / "reference" / "local.pdf").write_text("placeholder")
            (rag_dir / "summary" / "sources" / "test.md").write_text(
                "[local](../reference/local.pdf)\n"
            )
            issues = check_dead_links(rag_dir)
            self.assertEqual(issues, [])

    def test_missing_pdf_ref(self):
        with tempfile.TemporaryDirectory() as td:
            rag_dir = Path(td)
            (rag_dir / "summary" / "sources").mkdir(parents=True)
            (rag_dir / "summary" / "sources" / "test.md").write_text(
                "---\ntype: source\ncreated: 2025-01-01\ntitle: T\n"
                'pdf: "reference/pdfs/missing.pdf"\n---\n'
            )
            issues = check_pdf_refs(rag_dir)
            self.assertTrue(any("missing PDF" in i.lower() or "missing pdf" in i.lower() for i in issues))

    def test_orphan_source(self):
        with tempfile.TemporaryDirectory() as td:
            rag_dir = Path(td)
            (rag_dir / "summary" / "sources").mkdir(parents=True)
            (rag_dir / "summary" / "sources" / "test.md").write_text(
                "---\ntype: source\ncreated: 2025-01-01\ntitle: T\n---\n"
            )
            issues = check_source_fm(rag_dir, {})
            self.assertTrue(any("orphan" in i.lower() for i in issues))

    def test_uncategorized_is_valid_vocabulary_tag(self):
        with tempfile.TemporaryDirectory() as td:
            rag_dir = Path(td)
            (rag_dir / "summary" / "sources").mkdir(parents=True)
            (rag_dir / "vocabulary.md").write_text(
                "# Controlled Vocabulary\n\n```yaml\nvocabulary:\n  methods:\n    uncategorized:\n      canonical: Uncategorized\n```\n"
            )
            (rag_dir / "summary" / "sources" / "test.md").write_text(
                "---\ntype: source\ncreated: 2025-01-01\ntitle: T\nmethods: [uncategorized]\n---\n"
            )
            issues = check_source_fm(rag_dir, load_vocabulary(rag_dir))
            self.assertFalse(any("off-vocab" in i.lower() for i in issues))

    def test_auto_block_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            rag_dir = Path(td)
            (rag_dir / "summary" / "sources").mkdir(parents=True)
            (rag_dir / "summary" / "sources" / "test.md").write_text(
                "<!-- AUTO:BEGIN -->\nstart\n<!-- AUTO:END -->\n<!-- AUTO:BEGIN -->\nstart2\n"
            )
            issues = check_auto_blocks(rag_dir)
            self.assertTrue(len(issues) >= 1)


if __name__ == "__main__":
    unittest.main()
