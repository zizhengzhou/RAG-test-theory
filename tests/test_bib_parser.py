"""Tests for bib_parser."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))
from bib_parser import parse_bibtex_file, parse_bibtex, render_bibtex

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestBibParser(unittest.TestCase):
    def test_parses_sample_bib(self):
        entries = parse_bibtex_file(FIXTURES / "sample.bib")
        self.assertGreaterEqual(len(entries), 3)
        keys = {e["ID"] for e in entries}
        self.assertIn("smith2023benchmark", keys)
        self.assertIn("chen2024improved", keys)
        self.assertIn("lee2024survey", keys)

    def test_extracts_fields(self):
        entries = parse_bibtex_file(FIXTURES / "sample.bib")
        smith = next(e for e in entries if e["ID"] == "smith2023benchmark")
        self.assertIn("benchmark", smith["title"].lower())
        self.assertIn("smith", smith["author"].lower())
        self.assertEqual(smith["year"], "2023")
        self.assertIn("10.1234", smith["doi"])

    def test_renders_bibtex(self):
        entries = parse_bibtex_file(FIXTURES / "sample.bib")
        entry = entries[0]
        rendered = render_bibtex(entry)
        self.assertIn("@article", rendered)
        self.assertIn(entry["ID"], rendered)

    def test_errors_on_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            parse_bibtex_file(Path("nonexistent.bib"))

    def test_parses_empty(self):
        entries = parse_bibtex("% a comment only\n@comment{test}\n")
        self.assertEqual(len(entries), 0)


if __name__ == "__main__":
    unittest.main()
