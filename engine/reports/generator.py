from __future__ import annotations

from typing import Any


def _names(items: list[dict], name_key: str) -> str:
    values = [x.get(name_key) for x in items if x.get(name_key)]
    return ", ".join(values) if values else "명확히 확인되지 않음"


def build_fallback_module1_report(structured_patent: dict) -> dict[str, Any]:
    """Deterministic safety fallback when the report-generation call fails."""
    claims = structured_patent.get("independent_claims", [])
    problems = structured_patent.get("problem_assertions", [])
    effects = structured_patent.get("effect_assertions", [])
    tech = structured_patent.get("technology_assignments", [])

    claim_reports = []
    for claim in claims:
        elements = []
        for e in claim.get("claim_elements", []):
            name = e.get("canonical_name") or e.get("original_expression") or "미매핑 구성요소"
            funcs = [
                f.get("canonical_function")
                for f in claim.get("function_assignments", [])
                if f.get("subject_instance_id") == e.get("element_instance_id") and f.get("canonical_function")
            ]
            explanation = f"청구항에 포함된 구성요소이며, 확인된 기능은 {', '.join(funcs)}입니다." if funcs else "청구항에 포함된 필수 구성요소입니다."
            elements.append(
                {
                    "name": name,
                    "original_expression": e.get("original_expression", ""),
                    "explanation": explanation,
                }
            )
        relation_texts = []
        for r in claim.get("relation_assertions", []):
            rel = r.get("canonical_relation") or "미매핑 관계"
            obj = r.get("object_instance_id") or ", ".join(r.get("object_set", []))
            relation_texts.append(f"{r.get('subject_instance_id')} --{rel}--> {obj}")
        claim_reports.append(
            {
                "claim_number": claim.get("claim_number"),
                "plain_explanation": claim.get("plain_summary") or "독립청구항 구조를 확인했습니다.",
                "claim_elements": elements,
                "relation_explanation": "; ".join(relation_texts) if relation_texts else "명시적으로 정규화된 관계가 확인되지 않았습니다.",
                "core_conditions": [x.get("normalized_expression") for x in claim.get("constraints", []) if x.get("normalized_expression")],
                "scope_note": "구성요소와 관계 및 조건을 함께 보아 청구항의 필수 구조를 이해해야 합니다.",
            }
        )

    primary_problem = next((x for x in problems if x.get("role") == "primary"), problems[0] if problems else None)
    primary_effect = next((x for x in effects if x.get("role") == "primary"), effects[0] if effects else None)
    primary_tech = next((x for x in tech if x.get("role") == "primary"), tech[0] if tech else None)

    return {
        "three_line_summary": {
            "what_is_patent": (claims[0].get("plain_summary") if claims else "독립청구항의 핵심 구조를 자동 요약하지 못했습니다."),
            "how_it_solves": f"주요 기술적 과제는 {primary_problem.get('korean_name') or primary_problem.get('canonical_problem')}입니다." if primary_problem else "명세서에서 핵심 과제를 명확히 정규화하지 못했습니다.",
            "key_point": f"대표 기술분류는 {primary_tech.get('technology_name')}입니다." if primary_tech else "대표 PSD 기술분류가 명확히 확인되지 않았습니다.",
        },
        "core_problem": f"{primary_problem.get('korean_name') or primary_problem.get('canonical_problem')}: {primary_problem.get('evidence', {}).get('evidence_text', '')}" if primary_problem else "핵심 과제가 명확히 식별되지 않았습니다.",
        "independent_claims": claim_reports,
        "dependent_claims": "종속청구항의 추가 제한사항: " + "; ".join(
            f"청구항 {x.get('claim_number')}: {', '.join(x.get('added_limitations', []))}"
            for x in structured_patent.get("dependent_claims", [])
        ) if structured_patent.get("dependent_claims") else "종속청구항의 추가 제한사항이 식별되지 않았습니다.",
        "operation_principle_steps": [
            x for claim in claims for x in [claim.get("plain_summary")] if x
        ] or ["구조화된 기능/관계 정보가 부족하여 작동 순서를 자동 구성하지 못했습니다."],
        "technical_effects": _names(effects, "korean_name"),
        "technology_classification": _names(tech, "technology_name"),
        "core_technology_summary": "Ontology 기반 구조화 결과를 바탕으로 생성된 기본 설명입니다. Report LLM 호출 실패로 상세 서술은 제한됩니다.",
        "evidence_note": "각 주장 근거는 Evidence 탭의 Claim/Specification 원문에서 확인할 수 있습니다.",
    }


def build_report(structured_patent: dict) -> dict:
    return build_fallback_module1_report(structured_patent)
