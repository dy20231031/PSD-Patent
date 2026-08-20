from __future__ import annotations

DEFAULT_WEIGHTS = {
    "technology": 0.20,
    "problem": 0.20,
    "function": 0.20,
    "claim_element": 0.15,
    "relation": 0.25,
}


def rerank_candidates(candidates: list[dict], target: dict) -> list[dict]:
    """Ontology similarity 기반 reranking placeholder."""
    return candidates
