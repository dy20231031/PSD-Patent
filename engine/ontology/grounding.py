from __future__ import annotations

from copy import deepcopy
from typing import Any


CLAIM_LEVELS = {"E1", "E2"}
PROBLEM_LEVELS = {"PE1", "PE2", "PE3"}
EFFECT_LEVELS = {"EE1", "EE2", "EE3"}


def _supported_evidence(item: dict[str, Any], allowed: set[str]) -> bool:
    evidence = item.get("evidence") or {}
    level = str(evidence.get("evidence_level") or "").upper()
    text = str(evidence.get("evidence_text") or "").strip()
    return level in allowed and bool(text)


def enforce_reporting_grounding(structured_patent: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Remove inference-only/ungrounded facts before report generation.

    The extractor already asks Gemini not to emit E4/PE4/EE4. This second layer
    turns that policy into code so a malformed or over-inferential model response
    cannot silently become a user-facing patent fact.
    """
    data = deepcopy(structured_patent)
    warnings: list[str] = []

    claim_fields = (
        "claim_elements",
        "relation_assertions",
        "function_assignments",
        "state_assertions",
        "mode_assertions",
        "constraints",
    )
    for claim in data.get("independent_claims", []) or []:
        claim_no = claim.get("claim_number")
        for field in claim_fields:
            kept = []
            for item in claim.get(field, []) or []:
                if _supported_evidence(item, CLAIM_LEVELS):
                    kept.append(item)
                else:
                    warnings.append(f"Claim {claim_no}: removed ungrounded {field} assertion")
            claim[field] = kept

    kept_problems = []
    for item in data.get("problem_assertions", []) or []:
        if _supported_evidence(item, PROBLEM_LEVELS):
            kept_problems.append(item)
        else:
            warnings.append("Removed Problem assertion without PE1-PE3 evidence")
    data["problem_assertions"] = kept_problems

    kept_effects = []
    for item in data.get("effect_assertions", []) or []:
        if _supported_evidence(item, EFFECT_LEVELS):
            kept_effects.append(item)
        else:
            warnings.append("Removed Effect assertion without EE1-EE3 evidence")
    data["effect_assertions"] = kept_effects

    data.setdefault("validation_warnings", [])
    data["validation_warnings"].extend(warnings)
    return data, warnings
