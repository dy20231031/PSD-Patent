from __future__ import annotations

from typing import Any


CONTEXT_POLICY = {
    "problem": ["abstract", "background", "summary"],
    "claim_elements": ["independent_claims"],
    "relations": ["independent_claims"],
    "constraints": ["independent_claims"],
    "dependent_limitations": ["dependent_claims"],
    "operation": ["claims", "description", "figure_description"],
    "effects": ["summary", "description"],
    "ontology_claims": ["independent_claims", "dependent_claims"],
    "problem_effect": ["abstract", "background", "summary", "description"],
}


def _clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    head = int(limit * 0.72)
    tail = limit - head
    return f"{text[:head]}\n\n...[context truncated]...\n\n{text[-tail:]}"


def _claim_text(claim: dict[str, Any]) -> str:
    dep = claim.get("depends_on") or []
    dep_text = f" depends_on={dep}" if dep else ""
    return (
        f"[Claim {claim.get('claim_number')} | {claim.get('claim_type')}{dep_text}]\n"
        f"{claim.get('text', '').strip()}"
    )


def route_context(parsed_patent: dict, task: str, max_chars: int = 70000) -> dict[str, Any]:
    """Return actual task-specific patent text instead of only section names."""
    claims = parsed_patent.get("claims", [])
    independent = [c for c in claims if c.get("claim_type") == "independent"]
    dependent = [c for c in claims if c.get("claim_type") == "dependent"]

    if task in {"ontology_claims", "claim_elements", "relations", "constraints", "dependent_limitations"}:
        parts: list[str] = []
        if task != "dependent_limitations":
            parts.append("## Independent Claims")
            parts.extend(_claim_text(c) for c in independent)
        if task in {"ontology_claims", "dependent_limitations"} and dependent:
            parts.append("## Dependent Claims")
            parts.extend(_claim_text(c) for c in dependent)
        text = "\n\n".join(parts)
    elif task in {"problem", "problem_effect"}:
        sections = [
            ("Abstract", parsed_patent.get("abstract", "")),
            ("Background", parsed_patent.get("background", "")),
            ("Summary", parsed_patent.get("summary", "")),
        ]
        if task == "problem_effect":
            sections.append(("Description", parsed_patent.get("description", "")))
        text = "\n\n".join(f"## {name}\n{body}" for name, body in sections if body)
    elif task == "effects":
        text = "\n\n".join(
            f"## {name}\n{body}"
            for name, body in [
                ("Summary", parsed_patent.get("summary", "")),
                ("Description", parsed_patent.get("description", "")),
            ]
            if body
        )
    elif task == "operation":
        claim_text = "\n\n".join(_claim_text(c) for c in claims)
        text = (
            f"## Claims\n{claim_text}\n\n"
            f"## Description\n{parsed_patent.get('description', '')}\n\n"
            f"## Figure Description\n{parsed_patent.get('figure_description', '')}"
        )
    else:
        text = parsed_patent.get("raw_text", "")

    clipped = _clip(text, max_chars)
    return {
        "task": task,
        "policy": CONTEXT_POLICY.get(task, []),
        "text": clipped,
        "original_char_count": len(text),
        "routed_char_count": len(clipped),
        "truncated": len(clipped) < len(text),
    }
