"""Tests for dedup and metadata normalizer."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))
from bib_parser import parse_bibtex_file
from dedup import deduplicate_entries, entry_dedup_key, compare_bibs
from metadata_normalizer import normalize_doi, normalize_arxiv, normalize_title

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestMetadataNormalizer(unittest.TestCase):
    def test_normalize_doi(self):
        self.assertEqual(normalize_doi("10.1234/jcp.2023.112345"), "10.1234/jcp.2023.112345")
        self.assertEqual(normalize_doi("DOI: 10.1234/jcp.2023.112345"), "10.1234/jcp.2023.112345")
        self.assertEqual(normalize_doi(""), "")

    def test_normalize_arxiv(self):
        self.assertEqual(normalize_arxiv("2301.12345"), "2301.12345")
        self.assertEqual(normalize_arxiv("arXiv:2301.12345v2"), "2301.12345v2")

    def test_normalize_title(self):
        a = normalize_title("  A Benchmark -- Study, of Numeric Methods for Quantum Scattering!")
        b = normalize_title("A benchmark study of numeric methods for quantum scattering")
        self.assertEqual(a, b)


class TestDedup(unittest.TestCase):
    def test_doi_match(self):
        left = parse_bibtex_file(FIXTURES / "sample.bib")
        right = parse_bibtex_file(FIXTURES / "duplicate.bib")
        dupes = compare_bibs(FIXTURES / "sample.bib", FIXTURES / "duplicate.bib")
        self.assertGreaterEqual(len(dupes), 1)

    def test_self_dedup(self):
        all_entries = parse_bibtex_file(FIXTURES / "sample.bib")
        unique, dups = deduplicate_entries(all_entries)
        self.assertEqual(len(unique), len(all_entries))
        self.assertEqual(len(dups), 0)

    def test_dedup_same_file_twice(self):
        combined = parse_bibtex_file(FIXTURES / "sample.bib") + parse_bibtex_file(FIXTURES / "sample.bib")
        unique, dups = deduplicate_entries(combined)
        self.assertEqual(len(unique), 3)
        self.assertEqual(len(dups), 3)


if __name__ == "__main__":
    unittest.main()
