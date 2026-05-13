"""Tests for embedding router fallback behavior."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))

from embedding_router import get_embedding, get_embeddings


class TestEmbeddingRouter(unittest.TestCase):
    @patch("embedding_router._load_sentence_transformer", side_effect=ImportError("missing"))
    def test_hash_fallback_without_ml_stack(self, _):
        result = get_embedding("test text")

        self.assertTrue(result.fallback_used)
        self.assertEqual(result.model, "hash-fallback")
        self.assertEqual(result.dimension, 128)

    @patch("embedding_router._load_sentence_transformer", side_effect=ImportError("missing"))
    def test_get_embeddings_batch(self, _):
        results = get_embeddings(["a", "b"])

        self.assertEqual(len(results), 2)
        self.assertTrue(all(result.fallback_used for result in results))


if __name__ == "__main__":
    unittest.main()
