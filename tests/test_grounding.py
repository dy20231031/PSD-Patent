from engine.ontology.grounding import enforce_reporting_grounding


def _e(level, text="evidence"):
    return {"evidence_level": level, "evidence_text": text}


def test_grounding_removes_inference_only_facts():
    structured = {
        "independent_claims": [{
            "claim_number": 1,
            "claim_elements": [
                {"canonical_name": "Motor", "evidence": _e("E1")},
                {"canonical_name": "Imagined Part", "evidence": _e("E4")},
            ],
            "relation_assertions": [], "function_assignments": [], "state_assertions": [],
            "mode_assertions": [], "constraints": [],
        }],
        "problem_assertions": [
            {"canonical_problem": "p1", "evidence": _e("PE3")},
            {"canonical_problem": "p2", "evidence": _e("PE4")},
        ],
        "effect_assertions": [
            {"canonical_effect": "e1", "evidence": _e("EE2")},
            {"canonical_effect": "e2", "evidence": _e("EE4")},
        ],
    }
    cleaned, warnings = enforce_reporting_grounding(structured)
    assert [x["canonical_name"] for x in cleaned["independent_claims"][0]["claim_elements"]] == ["Motor"]
    assert [x["canonical_problem"] for x in cleaned["problem_assertions"]] == ["p1"]
    assert [x["canonical_effect"] for x in cleaned["effect_assertions"]] == ["e1"]
    assert warnings
