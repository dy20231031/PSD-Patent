from __future__ import annotations

import re
from typing import Any


_STOPWORDS = {
    "figure", "fig", "shows", "showing", "illustrates", "illustrating", "view",
    "embodiment", "invention", "assembly", "device", "system", "vehicle", "door",
    "with", "from", "into", "about", "including", "according", "portion", "perspective",
    "cross", "sectional", "schematic", "exploded",
}


def _tokens(text: str | None) -> set[str]:
    values = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}|[가-힣]{2,}", (text or "").lower())
    return {x.replace("_", " ") for x in values if x not in _STOPWORDS}


def _analysis_keywords(result: dict[str, Any]) -> set[str]:
    words: set[str] = set()
    words |= _tokens(result.get("primary_technology"))
    report = result.get("module1_report") or {}
    words |= _tokens(report.get("core_problem"))
    words |= _tokens(report.get("core_technology_summary"))
    for step in report.get("operation_principle_steps") or []:
        words |= _tokens(step)
    for claim in report.get("independent_claims") or []:
        words |= _tokens(claim.get("plain_explanation"))
        words |= _tokens(claim.get("relation_explanation"))
        for element in claim.get("claim_elements") or []:
            words |= _tokens(element.get("name"))
            words |= _tokens(element.get("original_expression"))
    return words


def select_representative_figures(result: dict[str, Any], *, limit: int = 3) -> list[dict[str, Any]]:
    """Choose a few real patent drawings for the public report.

    Selection is intentionally evidence-safe: it uses only the patent's own
    figure captions plus already-generated Module 1 terms. It does not infer new
    facts from pixels. FIG. 1 receives a small overview prior because patent
    specifications commonly use it for the system-level view.
    """
    raw = result.get("raw_patent") or {}
    figures = raw.get("figures") or []
    if not figures:
        return []

    keywords = _analysis_keywords(result)
    scored: list[tuple[float, int, dict[str, Any]]] = []
    for idx, figure in enumerate(figures):
        caption_tokens = _tokens(figure.get("caption"))
        overlap = len(caption_tokens & keywords)
        score = float(overlap * 3)
        number = figure.get("figure_number")
        if number == 1:
            score += 3.5
        elif number in {2, 3}:
            score += 1.0
        if figure.get("caption"):
            score += 0.5
        scored.append((score, -idx, figure))

    chosen = [x[2] for x in sorted(scored, key=lambda x: (x[0], x[1]), reverse=True)[: max(1, limit)]]
    return chosen
