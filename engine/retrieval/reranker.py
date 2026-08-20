from __future__ import annotations

from typing import Any

DEFAULT_WEIGHTS = {
    "technology": 0.15,
    "problem": 0.20,
    "function": 0.20,
    "claim_element": 0.15,
    "relation": 0.25,
    "architecture": 0.05,
}


def _set(values) -> set[str]:
    return {str(v).strip() for v in (values or []) if str(v).strip()}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def build_target_fingerprint(structured_patent: dict) -> dict[str, list[str]]:
    technology_ids = [
        x.get("technology_id")
        for x in structured_patent.get("technology_assignments", [])
        if x.get("technology_id")
    ]
    architecture_ids = [
        x.get("architecture_id")
        for x in structured_patent.get("architecture_assignments", [])
        if x.get("architecture_id")
    ]
    problem_ids = [
        x.get("problem_id")
        for x in structured_patent.get("problem_assertions", [])
        if x.get("problem_id")
    ]
    function_ids: list[str] = []
    claim_element_ids: list[str] = []
    relation_ids: list[str] = []
    for claim in structured_patent.get("independent_claims", []):
        function_ids.extend(
            x.get("function_id") for x in claim.get("function_assignments", []) if x.get("function_id")
        )
        claim_element_ids.extend(
            x.get("master_element_id") for x in claim.get("claim_elements", []) if x.get("master_element_id")
        )
        relation_ids.extend(
            x.get("relation_id") for x in claim.get("relation_assertions", []) if x.get("relation_id")
        )
    return {
        "technology_ids": sorted(_set(technology_ids)),
        "architecture_ids": sorted(_set(architecture_ids)),
        "problem_ids": sorted(_set(problem_ids)),
        "function_ids": sorted(_set(function_ids)),
        "claim_element_ids": sorted(_set(claim_element_ids)),
        "relation_ids": sorted(_set(relation_ids)),
    }


def score_candidate(
    candidate_fingerprint: dict,
    target_fingerprint: dict,
    *,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    weights = dict(weights or DEFAULT_WEIGHTS)
    mapping = {
        "technology": "technology_ids",
        "problem": "problem_ids",
        "function": "function_ids",
        "claim_element": "claim_element_ids",
        "relation": "relation_ids",
        "architecture": "architecture_ids",
    }
    active_weight = 0.0
    components: dict[str, float] = {}
    for dimension, field in mapping.items():
        target_values = _set(target_fingerprint.get(field, []))
        candidate_values = _set(candidate_fingerprint.get(field, []))
        if not target_values:
            components[dimension] = 0.0
            continue
        w = float(weights.get(dimension, 0.0))
        active_weight += w
        components[dimension] = _jaccard(target_values, candidate_values)

    if active_weight <= 0:
        overall = 0.0
    else:
        overall = sum(
            components[dimension] * float(weights.get(dimension, 0.0))
            for dimension in mapping
        ) / active_weight

    return {
        "score": round(overall * 100, 1),
        "score_breakdown": {k: round(v * 100, 1) for k, v in components.items()},
    }


def rerank_candidates(
    candidates: list[dict],
    target_fingerprint: dict,
    *,
    weights: dict[str, float] | None = None,
) -> list[dict]:
    ranked: list[dict] = []
    for candidate in candidates:
        fingerprint = candidate.get("fingerprint") or {}
        scored = score_candidate(fingerprint, target_fingerprint, weights=weights)
        item = dict(candidate)
        item.update(scored)
        ranked.append(item)
    return sorted(
        ranked,
        key=lambda x: (x.get("score", 0.0), -float(x.get("best_search_rank", 999))),
        reverse=True,
    )
