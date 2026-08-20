from __future__ import annotations


CONTEXT_POLICY = {
    "problem": ["abstract", "background", "summary"],
    "claim_elements": ["independent_claims"],
    "relations": ["independent_claims"],
    "constraints": ["independent_claims"],
    "dependent_limitations": ["dependent_claims"],
    "operation": ["claims", "description", "figure_description"],
    "effects": ["summary", "description"],
}


def route_context(parsed_patent: dict, task: str) -> dict:
    """Task별 필요한 patent context만 선택한다."""
    return {"task": task, "sections": CONTEXT_POLICY.get(task, [])}
