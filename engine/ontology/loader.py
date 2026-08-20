from __future__ import annotations

import json
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge"
KNOWLEDGE_FILES = [
    "taxonomy.json", "claim_elements.json", "functions.json", "relations.json",
    "states_modes.json", "constraints.json", "problems.json",
    "effects_design_attributes.json", "ontology_meta.json",
]

def load_json(name: str):
    path = KNOWLEDGE_DIR / name
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_all_knowledge() -> dict[str, dict]:
    return {name.removesuffix(".json"): load_json(name) for name in KNOWLEDGE_FILES}

def build_canonical_indexes() -> dict[str, dict[str, dict]]:
    kb=load_all_knowledge()
    return {
        "claim_elements": {x["canonical_name"]: x for x in kb["claim_elements"]["items"]},
        "functions": {x["canonical_name"]: x for x in kb["functions"]["items"]},
        "relations": {x["canonical_name"]: x for x in kb["relations"]["items"]},
        "problems": {x["canonical_name"]: x for x in kb["problems"]["items"]},
        "effects": {x["canonical_name"]: x for x in kb["effects_design_attributes"]["effects"]},
    }
