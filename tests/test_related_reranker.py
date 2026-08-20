from engine.retrieval.reranker import build_target_fingerprint, score_candidate


def test_ontology_similarity_rewards_relation_problem_function_overlap():
    structured = {
        "technology_assignments": [{"technology_id": "T2.6"}],
        "architecture_assignments": [],
        "problem_assertions": [{"problem_id": "P-FLX-01"}],
        "independent_claims": [
            {
                "claim_elements": [{"master_element_id": "CE-CAB-001"}, {"master_element_id": "CE-PUL-004"}],
                "function_assignments": [{"function_id": "F-FLX-09"}],
                "relation_assertions": [{"relation_id": "R-MOT-06"}],
            }
        ],
    }
    target = build_target_fingerprint(structured)
    good = {
        "technology_ids": ["T2.6"],
        "problem_ids": ["P-FLX-01"],
        "function_ids": ["F-FLX-09"],
        "claim_element_ids": ["CE-CAB-001", "CE-PUL-004"],
        "relation_ids": ["R-MOT-06"],
        "architecture_ids": [],
    }
    weak = {
        "technology_ids": ["T2.6"],
        "problem_ids": [],
        "function_ids": [],
        "claim_element_ids": ["CE-CAB-001"],
        "relation_ids": [],
        "architecture_ids": [],
    }
    assert score_candidate(good, target)["score"] > score_candidate(weak, target)["score"]
