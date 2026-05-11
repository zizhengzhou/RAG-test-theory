"""Tests for rdf_parser."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))
from rdf_parser import parse_rdf

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestRdfParser(unittest.TestCase):
    def test_parses_entries(self):
        items = parse_rdf(FIXTURES / "zotero-rdf-minimal" / "exported-items.rdf")
        self.assertGreaterEqual(len(items), 1)

    def test_extracts_title(self):
        items = parse_rdf(FIXTURES / "zotero-rdf-minimal" / "exported-items.rdf")
        titles = [i["title"].lower() for i in items]
        self.assertTrue(any("benchmark" in t for t in titles))

    def test_extracts_authors(self):
        items = parse_rdf(FIXTURES / "zotero-rdf-minimal" / "exported-items.rdf")
        self.assertTrue(any(len(i["authors"]) >= 1 for i in items))

    def test_extracts_identifiers(self):
        items = parse_rdf(FIXTURES / "zotero-rdf-minimal" / "exported-items.rdf")
        self.assertTrue(any("doi" in i["identifiers"] or "arxiv" in i["identifiers"] for i in items))

    def test_extracts_attachments(self):
        items = parse_rdf(FIXTURES / "zotero-rdf-minimal" / "exported-items.rdf")
        self.assertTrue(any(len(i["attachments"]) >= 1 for i in items))


if __name__ == "__main__":
    unittest.main()
