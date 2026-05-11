"""Tests for provider-backed literature search."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

import external_search


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.text.encode("utf-8")


class TestExternalSearch(unittest.TestCase):
    def test_search_inspire_parses_results(self):
        payload = {
            "hits": {
                "hits": [
                    {
                        "id": "3134110",
                        "metadata": {
                            "control_number": 3134110,
                            "titles": [{"title": "Prospect of the NUCLEUS Experiment"}],
                            "authors": [{"full_name": "Abele, H."}, {"full_name": "Angloher, G."}],
                            "arxiv_eprints": [{"value": "2603.24450"}],
                            "dois": [{"value": "10.48550/arXiv.2603.24450"}],
                            "preprint_date": "2026-03-25",
                        },
                    }
                ]
            }
        }
        with patch("urllib.request.urlopen", return_value=FakeResponse(json.dumps(payload))):
            results = external_search.search_inspire("arxiv:2603.24450", size=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].record_id, "3134110")
        self.assertEqual(results[0].title, "Prospect of the NUCLEUS Experiment")
        self.assertEqual(results[0].arxiv, "2603.24450")
        self.assertEqual(results[0].year, "2026")

    def test_identifier_search_prefers_arxiv(self):
        calls = []

        def fake_urlopen(request, timeout=20):
            calls.append(request.full_url)
            return FakeResponse('{"hits":{"hits":[]}}')

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            external_search.search_inspire_by_identifier(doi="10.123/example", arxiv="2603.24450", size=3)
        self.assertIn("arxiv%3A2603.24450", calls[0])
        self.assertIn("size=3", calls[0])

    def test_fetch_inspire_bibtex(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse("@article{NUCLEUS:2026pnv,}\n")) as mocked:
            bibtex = external_search.fetch_inspire_bibtex("3134110")
        self.assertEqual(bibtex, "@article{NUCLEUS:2026pnv,}")
        self.assertIn("/3134110?format=bibtex", mocked.call_args[0][0].full_url)


if __name__ == "__main__":
    unittest.main()
