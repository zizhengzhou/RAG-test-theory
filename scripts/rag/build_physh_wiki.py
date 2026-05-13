"""Compatibility wrapper for strict PhySH-only vocabulary wiki generation."""

from __future__ import annotations

from pathlib import Path

from build_vocabulary_wiki import apply_vocabulary_wiki_plan, build_vocabulary_wiki_plan, plan_as_dict


def build_physh_wiki_plan(rag_dir: Path):
    return build_vocabulary_wiki_plan(rag_dir, strict_physh=True)


def apply_physh_wiki_plan(plan):
    return apply_vocabulary_wiki_plan(plan)
