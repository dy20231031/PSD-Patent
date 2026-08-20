from __future__ import annotations

import json
from typing import Any


def _dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def build_claim_knowledge_context(kb: dict[str, dict]) -> str:
    ce = [
        {
            "id": x["id"],
            "name": x["canonical_name"],
            "type": x.get("type"),
            "synonyms": x.get("synonyms", []),
            "definition": x.get("definition", ""),
        }
        for x in kb["claim_elements"]["items"]
    ]
    fn = [
        {
            "id": x["id"],
            "name": x["canonical_name"],
            "ko": x.get("korean_name"),
            "definition": x.get("definition", ""),
        }
        for x in kb["functions"]["items"]
    ]
    rel = [
        {
            "id": x["id"],
            "name": x["canonical_name"],
            "ko": x.get("korean_name"),
            "definition": x.get("definition_distinction", ""),
        }
        for x in kb["relations"]["items"]
    ]
    states = kb["states_modes"]["state_dimensions"]
    modes = kb["states_modes"]["operation_modes"]
    constraints = kb["constraints"]["items"]
    operators = kb["constraints"]["operators"]
    return _dumps(
        {
            "claim_elements": ce,
            "functions": fn,
            "relations": rel,
            "state_dimensions": states,
            "operation_modes": modes,
            "constraint_types": constraints,
            "constraint_operators": operators,
        }
    )


def build_problem_effect_context(kb: dict[str, dict]) -> str:
    problems = [
        {
            "id": x["id"],
            "name": x["canonical_name"],
            "ko": x.get("korean_name"),
            "definition": x.get("definition", ""),
            "distinction": x.get("distinction_rule", ""),
        }
        for x in kb["problems"]["items"]
    ]
    effects = [
        {
            "id": x["id"],
            "name": x["canonical_name"],
            "ko": x.get("korean_name"),
            "definition": x.get("definition", ""),
        }
        for x in kb["effects_design_attributes"]["effects"]
    ]
    das = [
        {"id": x["id"], "name": x.get("name") or x.get("canonical_name"), "ko": x.get("korean_name")}
        for x in kb["effects_design_attributes"]["design_attributes"]
    ]
    return _dumps({"problems": problems, "effects": effects, "design_attributes": das})


def build_taxonomy_context(kb: dict[str, dict]) -> str:
    tech = [
        {
            "id": x["id"],
            "name": x["name"],
            "parent_id": x.get("parent_id"),
            "level": x.get("level"),
            "definition": x.get("definition", ""),
        }
        for x in kb["taxonomy"]["technology_nodes"]
    ]
    arch = [
        {"id": x["id"], "name": x["name"], "parent_id": x.get("parent_id"), "definition": x.get("definition", "")}
        for x in kb["taxonomy"]["architecture_values"]
    ]
    return _dumps({"technologies": tech, "architecture_values": arch})
