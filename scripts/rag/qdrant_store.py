"""Qdrant storage helpers for DARW evidence chunks.

The module is intentionally import-safe when qdrant-client is not installed.
Dry-run mode validates payloads and returns planned operations without network
or service dependencies.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from embedding_router import get_embedding

COLLECTION = "darw_evidence_chunks"


@dataclass
class StorePlan:
    collection: str
    points: int
    dry_run: bool
    chunk_ids: list[str]


def load_chunk_records(jsonl_path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def build_upsert_plan(jsonl_path: Path, *, dry_run: bool = True) -> StorePlan:
    records = load_chunk_records(jsonl_path)
    return StorePlan(
        collection=COLLECTION,
        points=len(records),
        dry_run=dry_run,
        chunk_ids=[str(record.get("chunk_id", "")) for record in records if record.get("chunk_id")],
    )


def upsert_chunks(jsonl_path: Path, *, dry_run: bool = True, url: str = "http://localhost:6333") -> StorePlan:
    plan = build_upsert_plan(jsonl_path, dry_run=dry_run)
    if dry_run:
        return plan
    try:
        from qdrant_client import QdrantClient  # type: ignore
        from qdrant_client.models import PointStruct, VectorParams, Distance  # type: ignore
    except Exception as exc:
        raise RuntimeError("qdrant-client is required for non-dry-run upsert") from exc

    records = load_chunk_records(jsonl_path)
    if not records:
        return plan
    first_embedding = get_embedding(str(records[0].get("text", "")))
    client = QdrantClient(url=url)
    client.recreate_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=first_embedding.dimension, distance=Distance.COSINE),
    )
    points = []
    for index, record in enumerate(records):
        embedding = first_embedding if index == 0 else get_embedding(str(record.get("text", "")))
        points.append(
            PointStruct(
                id=str(record.get("chunk_id", index)),
                vector=embedding.vector,
                payload=record,
            )
        )
    client.upsert(collection_name=COLLECTION, points=points)
    return plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upsert DARW chunks into Qdrant")
    parser.add_argument("--chunks", required=True)
    parser.add_argument("--url", default="http://localhost:6333")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    dry_run = args.dry_run or not args.yes
    plan = upsert_chunks(Path(args.chunks).resolve(), dry_run=dry_run, url=args.url)
    data = plan.__dict__
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"qdrant plan: collection={plan.collection} points={plan.points} dry_run={plan.dry_run}")
    if dry_run:
        print("[dry-run] no Qdrant writes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
