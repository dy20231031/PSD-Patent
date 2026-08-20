from __future__ import annotations

import json
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge"

EXPECTED = {
    "claim_elements.json": ("items", 144),
    "functions.json": ("items", 69),
    "relations.json": ("items", 46),
    "problems.json": ("items", 47),
}

def _load(name: str):
    with (KNOWLEDGE_DIR/name).open("r", encoding="utf-8") as f:
        return json.load(f)

def validate_knowledge_base() -> list[str]:
    errors: list[str] = []
    for name,(key,count) in EXPECTED.items():
        data=_load(name)
        vals=data.get(key,[])
        if len(vals)!=count:
            errors.append(f"{name}: expected {count} {key}, got {len(vals)}")
        ids=[x.get("id") for x in vals if isinstance(x,dict) and x.get("id")]
        if len(ids)!=len(set(ids)):
            errors.append(f"{name}: duplicate IDs")

    ce=_load("claim_elements.json")
    ce_ids={x["id"] for x in ce["items"]}
    for x in ce["items"]:
        bid=x.get("broader_concept_id")
        if bid and bid not in ce_ids:
            errors.append(f"claim_elements: unresolved broader_concept_id {bid}")

    tax=_load("taxonomy.json")
    tax_ids={x["id"] for x in tax["technology_nodes"]} | {x["id"] for x in tax["architecture_axes"]} | {x["id"] for x in tax["architecture_values"]}
    for x in ce["items"]:
        for tid in x.get("taxonomy_hints",[]):
            if tid not in tax_ids:
                errors.append(f"claim_elements: unknown taxonomy hint {tid} on {x['id']}")

    sm=_load("states_modes.json")
    if len(sm.get("state_dimensions",[]))!=10: errors.append("states_modes: expected 10 state dimensions")
    if len(sm.get("operation_modes",[]))!=4: errors.append("states_modes: expected 4 operation modes")
    co=_load("constraints.json")
    if len(co.get("items",[]))!=12: errors.append("constraints: expected 12 constraint types")
    if len(co.get("operators",[]))!=18: errors.append("constraints: expected 18 operators")
    if len(co.get("context_qualifiers",[]))!=8: errors.append("constraints: expected 8 context qualifiers")
    ef=_load("effects_design_attributes.json")
    if len(ef.get("effects",[]))!=65: errors.append("effects: expected 65 effects")
    if len(ef.get("design_attributes",[]))!=20: errors.append("effects: expected 20 design attributes")
    on=_load("ontology_meta.json")
    if len(on.get("validation_rules",[]))!=15: errors.append("ontology: expected 15 validation rules")
    return errors

def validate_structured_patent(data: dict) -> list[str]:
    errors: list[str] = []
    ce=_load("claim_elements.json"); valid_ce={x["id"] for x in ce["items"]}
    rel=_load("relations.json"); valid_rel={x["canonical_name"] for x in rel["items"]}
    states=_load("states_modes.json"); state_values={x["canonical_name"]:set(x["controlled_values"]) for x in states["state_dimensions"]}

    for claim in data.get("claims",[]):
        instance_ids={x.get("element_instance_id") for x in claim.get("claim_elements",[]) if x.get("element_instance_id")}
        for e in claim.get("claim_elements",[]):
            mid=e.get("master_element_id")
            if mid and mid not in valid_ce:
                errors.append(f"V01 unknown master_element_id: {mid}")
        for r in claim.get("relation_assertions",[]):
            if r.get("subject") not in instance_ids:
                errors.append(f"V02 unknown relation subject: {r.get('subject')}")
            for oid in ([r.get("object")] if r.get("object") else []) + r.get("object_set",[]):
                if oid not in instance_ids:
                    errors.append(f"V02 unknown relation object: {oid}")
            if r.get("predicate") not in valid_rel:
                errors.append(f"V03 unknown relation predicate: {r.get('predicate')}")
        for s in claim.get("state_assertions",[]):
            dim=s.get("state_dimension") or s.get("state_type")
            val=s.get("state_value")
            if dim not in state_values or val not in state_values.get(dim,set()):
                errors.append(f"V04 invalid state: {dim}={val}")
    for ev in data.get("evidence",[]):
        lvl=ev.get("evidence_level")
        if lvl in {"E1","E2"} and not ev.get("claim_id"):
            errors.append(f"V06 {lvl} evidence requires claim_id")
    return errors
