"""Tests for deterministic DARW chunking."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from chunker import build_chunks, classify_section_type, stable_anchor


class TestChunker(unittest.TestCase):
    def test_stable_anchor(self):
        self.assertEqual(stable_anchor("Calculation of the Recoil Spectrum"), "#calculation-of-the-recoil-spectrum")

    def test_chunk_ids_are_stable(self):
        manifest = {
            "doc_id": "arxiv:2301.12345",
            "citation_key": "paper",
            "route": "arxiv_source",
            "parser": "arxiv2md",
            "source_sha256": "abc",
        }
        text = "# Intro\n\nFirst paragraph.\n\n$$E = mc^2$$\n\n# Method\n\nSecond paragraph.\n"
        first = build_chunks(manifest, text, max_chars=80)
        second = build_chunks(manifest, text, max_chars=80)
        self.assertEqual([c.chunk_id for c in first], [c.chunk_id for c in second])
        self.assertTrue(any(c.contains_equation for c in first))
        eq_chunks = [c for c in first if c.contains_equation]
        self.assertTrue(eq_chunks[0].equation_ids[0].startswith("eq-intro-"))

    def test_char_ranges_match_text(self):
        manifest = {"doc_id": "pdf:paper", "citation_key": "paper", "route": "pdf_pymupdf", "parser": "pymupdf4llm", "source_sha256": "abc"}
        text = "# Intro\n\nEvidence text.\n"
        chunks = build_chunks(manifest, text)
        self.assertEqual(text[chunks[0].char_start:chunks[0].char_end].strip(), chunks[0].text)

    def test_section_type_classification(self):
        self.assertEqual(classify_section_type("References"), "references")
        self.assertEqual(classify_section_type("Online content"), "metadata")
        self.assertEqual(classify_section_type("Results"), "results")
        self.assertEqual(
            classify_section_type(
                "Parsed PDF text",
                "[1] First reference.\n[2] Second reference.\n[3] Third reference.\n",
            ),
            "references",
        )
        self.assertEqual(classify_section_type("Document", "---\ndoc_id: paper\ncitation_key: paper\n---"), "metadata")


if __name__ == "__main__":
    unittest.main()
