from engine.ontology.loader import load_all_knowledge
from engine.ontology.mapper import normalize_ontology_extraction


def _ev(level="E1"):
    return {"source_section": "Claim", "claim_id": "C1", "evidence_text": "a drive cable", "evidence_level": level}


def test_mapper_resolves_known_ids_and_preserves_unmapped_candidates():
    kb = load_all_knowledge()
    claim = {
        "independent_claims": [
            {
                "claim_id": "C1",
                "claim_number": 1,
                "plain_summary": "테스트",
                "claim_elements": [
                    {
                        "element_instance_id": "DriveCable_1",
                        "master_element_id": None,
                        "canonical_name": "Drive Cable",
                        "original_expression": "drive cable",
                        "element_type": "Component",
                        "instance_index": 1,
                        "role": None,
                        "position": None,
                        "attributes": [],
                        "normalization_status": "exact",
                        "evidence": _ev(),
                    },
                    {
                        "element_instance_id": "Mystery_1",
                        "master_element_id": "CE-NOT-REAL",
                        "canonical_name": "Mystery Widget",
                        "original_expression": "mystery widget",
                        "element_type": None,
                        "instance_index": None,
                        "role": None,
                        "position": None,
                        "attributes": [],
                        "normalization_status": "exact",
                        "evidence": _ev(),
                    },
                ],
                "relation_assertions": [],
                "function_assignments": [],
                "state_assertions": [],
                "mode_assertions": [],
                "constraints": [],
            }
        ],
        "dependent_claims": [],
    }
    pe = {"problems": [], "effects": []}
    tech = {"technology_assignments": [], "architecture_assignments": []}
    structured, warnings = normalize_ontology_extraction(claim, pe, tech, kb)
    elements = structured["independent_claims"][0]["claim_elements"]
    assert elements[0]["master_element_id"] is not None
    assert elements[0]["canonical_name"] == "Drive Cable"
    assert elements[1]["master_element_id"] is None
    assert elements[1]["normalization_status"] == "unmapped_candidate"
    assert any("UNMAPPED_ELEMENT" in w for w in warnings)
