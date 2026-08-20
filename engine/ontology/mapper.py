from __future__ import annotations

from copy import deepcopy
from typing import Any


def _index(items: list[dict[str, Any]], name_key: str = "canonical_name") -> tuple[dict[str, dict], dict[str, dict]]:
    by_id = {x["id"]: x for x in items if x.get("id")}
    by_name = {str(x.get(name_key, "")).casefold(): x for x in items if x.get(name_key)}
    return by_id, by_name


def _synonym_index(items: list[dict[str, Any]]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for item in items:
        for synonym in item.get("synonyms", []):
            out[str(synonym).casefold()] = item
    return out


def _resolve(record: dict, *, id_field: str, name_field: str, by_id: dict, by_name: dict, synonyms: dict | None = None) -> None:
    rid = record.get(id_field)
    name = record.get(name_field)
    target = by_id.get(rid) if rid else None
    if target is None and name:
        target = by_name.get(str(name).casefold())
    if target is None and synonyms and record.get("original_expression"):
        target = synonyms.get(str(record["original_expression"]).casefold())
        if target is not None:
            record["normalization_status"] = "synonym"
    if target is not None:
        record[id_field] = target["id"]
        canonical = target.get("canonical_name") or target.get("name")
        record[name_field] = canonical
        if record.get("normalization_status") == "unmapped_candidate":
            record["normalization_status"] = "exact"
    else:
        record[id_field] = None
        record[name_field] = None
        record["normalization_status"] = "unmapped_candidate"


def normalize_ontology_extraction(
    claim_extraction: dict,
    problem_effect: dict,
    technology: dict,
    knowledge_base: dict,
) -> tuple[dict, list[str]]:
    """Validate model-selected canonical IDs against the frozen JSON KB.

    Unknown concepts are never forced into the nearest vocabulary entry. They
    remain `unmapped_candidate` and are surfaced in validation warnings.
    """
    claim_extraction = deepcopy(claim_extraction)
    problem_effect = deepcopy(problem_effect)
    technology = deepcopy(technology)
    warnings: list[str] = []

    ce_items = knowledge_base["claim_elements"]["items"]
    ce_id, ce_name = _index(ce_items)
    ce_syn = _synonym_index(ce_items)
    fn_id, fn_name = _index(knowledge_base["functions"]["items"])
    rel_id, rel_name = _index(knowledge_base["relations"]["items"])
    pr_id, pr_name = _index(knowledge_base["problems"]["items"])
    ef_id, ef_name = _index(knowledge_base["effects_design_attributes"]["effects"])
    state_id, state_name = _index(knowledge_base["states_modes"]["state_dimensions"])
    mode_id, mode_name = _index(knowledge_base["states_modes"]["operation_modes"])
    con_id, con_name = _index(knowledge_base["constraints"]["items"])

    tech_items = knowledge_base["taxonomy"]["technology_nodes"]
    tech_by_id = {x["id"]: x for x in tech_items}
    tech_by_name = {x["name"].casefold(): x for x in tech_items}
    arch_items = knowledge_base["taxonomy"]["architecture_values"]
    arch_by_id = {x["id"]: x for x in arch_items}
    arch_by_name = {x["name"].casefold(): x for x in arch_items}

    valid_operators = {x.get("canonical_name") or x.get("operator") for x in knowledge_base["constraints"]["operators"]}
    valid_da = {x["id"] for x in knowledge_base["effects_design_attributes"]["design_attributes"]}

    claims = claim_extraction.get("independent_claims", [])
    for claim in claims:
        instance_ids: set[str] = set()
        for element in claim.get("claim_elements", []):
            _resolve(
                element,
                id_field="master_element_id",
                name_field="canonical_name",
                by_id=ce_id,
                by_name=ce_name,
                synonyms=ce_syn,
            )
            instance_ids.add(element.get("element_instance_id"))
            if element.get("master_element_id") is None:
                warnings.append(
                    f"UNMAPPED_ELEMENT {claim.get('claim_id')}: {element.get('original_expression')}"
                )

        for relation in claim.get("relation_assertions", []):
            _resolve(relation, id_field="relation_id", name_field="canonical_relation", by_id=rel_id, by_name=rel_name)
            if relation.get("relation_id") is None:
                warnings.append(
                    f"UNMAPPED_RELATION {claim.get('claim_id')}: {relation.get('evidence', {}).get('evidence_text', '')[:80]}"
                )
            refs = [relation.get("subject_instance_id"), relation.get("object_instance_id")] + relation.get("object_set", [])
            for ref in [r for r in refs if r]:
                if ref not in instance_ids:
                    warnings.append(f"INVALID_INSTANCE_REFERENCE {claim.get('claim_id')}: {ref}")

        for function in claim.get("function_assignments", []):
            _resolve(function, id_field="function_id", name_field="canonical_function", by_id=fn_id, by_name=fn_name)
            if function.get("function_id") is None:
                warnings.append(
                    f"UNMAPPED_FUNCTION {claim.get('claim_id')}: {function.get('evidence', {}).get('evidence_text', '')[:80]}"
                )

        for state in claim.get("state_assertions", []):
            _resolve(state, id_field="state_dimension_id", name_field="state_dimension", by_id=state_id, by_name=state_name)
            target = state_id.get(state.get("state_dimension_id")) if state.get("state_dimension_id") else None
            if target and state.get("state_value") not in target.get("controlled_values", []):
                warnings.append(
                    f"INVALID_STATE_VALUE {claim.get('claim_id')}: {state.get('state_dimension')}={state.get('state_value')}"
                )
                state["normalization_status"] = "unmapped_candidate"

        for mode in claim.get("mode_assertions", []):
            _resolve(mode, id_field="mode_id", name_field="canonical_mode", by_id=mode_id, by_name=mode_name)

        for constraint in claim.get("constraints", []):
            _resolve(
                constraint,
                id_field="constraint_type_id",
                name_field="canonical_constraint_type",
                by_id=con_id,
                by_name=con_name,
            )
            op = constraint.get("operator")
            if op and op not in valid_operators:
                warnings.append(f"UNMAPPED_CONSTRAINT_OPERATOR {claim.get('claim_id')}: {op}")
                constraint["operator"] = None

    for problem in problem_effect.get("problems", []):
        _resolve(problem, id_field="problem_id", name_field="canonical_problem", by_id=pr_id, by_name=pr_name)
        if problem.get("problem_id"):
            problem["korean_name"] = pr_id[problem["problem_id"]].get("korean_name")
        else:
            problem["korean_name"] = None
            warnings.append(f"UNMAPPED_PROBLEM: {problem.get('evidence', {}).get('evidence_text', '')[:80]}")

    for effect in problem_effect.get("effects", []):
        _resolve(effect, id_field="effect_id", name_field="canonical_effect", by_id=ef_id, by_name=ef_name)
        if effect.get("effect_id"):
            effect["korean_name"] = ef_id[effect["effect_id"]].get("korean_name")
        else:
            effect["korean_name"] = None
            warnings.append(f"UNMAPPED_EFFECT: {effect.get('evidence', {}).get('evidence_text', '')[:80]}")
        effect["design_attribute_ids"] = [x for x in effect.get("design_attribute_ids", []) if x in valid_da]

    for item in technology.get("technology_assignments", []):
        target = tech_by_id.get(item.get("technology_id"))
        if target is None and item.get("technology_name"):
            target = tech_by_name.get(str(item["technology_name"]).casefold())
        if target:
            item["technology_id"] = target["id"]
            item["technology_name"] = target["name"]
        else:
            warnings.append(f"UNMAPPED_TECHNOLOGY: {item.get('technology_name')}")
            item["technology_id"] = None
            item["technology_name"] = None

    for item in technology.get("architecture_assignments", []):
        target = arch_by_id.get(item.get("architecture_id"))
        if target is None and item.get("architecture_name"):
            target = arch_by_name.get(str(item["architecture_name"]).casefold())
        if target:
            item["architecture_id"] = target["id"]
            item["architecture_name"] = target["name"]
        else:
            warnings.append(f"UNMAPPED_ARCHITECTURE: {item.get('architecture_name')}")
            item["architecture_id"] = None
            item["architecture_name"] = None

    structured = {
        "schema_version": "structured-patent-v0.2",
        "independent_claims": claims,
        "dependent_claims": claim_extraction.get("dependent_claims", []),
        "problem_assertions": problem_effect.get("problems", []),
        "effect_assertions": problem_effect.get("effects", []),
        "technology_assignments": technology.get("technology_assignments", []),
        "architecture_assignments": technology.get("architecture_assignments", []),
        "validation_warnings": warnings,
    }
    return structured, warnings


def map_to_psd_ontology(extracted: dict, knowledge_base: dict) -> dict:
    """Backward-compatible helper retained for the starter API."""
    return extracted
