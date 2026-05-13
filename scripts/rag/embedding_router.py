"""Optional embedding backend router with deterministic fallback."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass


PREFERRED_MODEL = "Alibaba-NLP/gte-Qwen2-1.5B-instruct"
FALLBACK_MODEL = "BAAI/bge-m3"
HASH_FALLBACK_MODEL = "hash-fallback"


@dataclass(frozen=True)
class EmbeddingResult:
    vector: list[float]
    model: str
    dimension: int
    device: str
    elapsed_ms: float
    fallback_used: bool


def _hash_embedding(text: str, dimension: int = 128) -> list[float]:
    vector: list[float] = []
    seed = text.encode("utf-8", "replace")
    counter = 0
    while len(vector) < dimension:
        digest = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        for byte in digest:
            vector.append((byte / 127.5) - 1.0)
            if len(vector) >= dimension:
                break
        counter += 1
    return vector


def _load_sentence_transformer(model_name: str):
    from sentence_transformers import SentenceTransformer  # type: ignore

    return SentenceTransformer(model_name)


def get_embedding(text: str, *, model_name: str = PREFERRED_MODEL) -> EmbeddingResult:
    started = time.perf_counter()
    try:
        model = _load_sentence_transformer(model_name)
        encoded = model.encode([text], normalize_embeddings=True)[0]
        vector = [float(value) for value in encoded.tolist()]
        device = str(getattr(model, "device", "unknown"))
        return EmbeddingResult(
            vector=vector,
            model=model_name,
            dimension=len(vector),
            device=device,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 3),
            fallback_used=False,
        )
    except Exception:
        vector = _hash_embedding(text)
        return EmbeddingResult(
            vector=vector,
            model=HASH_FALLBACK_MODEL,
            dimension=len(vector),
            device="cpu",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 3),
            fallback_used=True,
        )


def get_embeddings(texts: list[str], *, model_name: str = PREFERRED_MODEL) -> list[EmbeddingResult]:
    return [get_embedding(text, model_name=model_name) for text in texts]
