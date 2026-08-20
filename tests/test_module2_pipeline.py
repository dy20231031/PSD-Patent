from engine.modules import module2


TARGET_STRUCTURED = {
    "patent": {"publication_number": "US99999999B2", "title": "Target PSD tension device"},
    "technology_assignments": [{"technology_id": "T2.6", "technology_name": "Tension / Slack Management", "role": "primary"}],
    "architecture_assignments": [],
    "problem_assertions": [{"problem_id": "P-FLX-01", "canonical_problem": "tension_loss_or_slack"}],
    "effect_assertions": [],
    "independent_claims": [
        {
            "claim_number": 1,
            "plain_summary": "케이블 장력 유지 구조",
            "claim_elements": [
                {"master_element_id": "CE-CAB-001", "canonical_name": "Drive Cable"},
                {"master_element_id": "CE-PUL-004", "canonical_name": "Tension Pulley"},
            ],
            "function_assignments": [{"function_id": "F-FLX-09", "canonical_function": "maintain_tension"}],
            "relation_assertions": [{"relation_id": "R-MOT-06", "canonical_relation": "applies_tension_to", "subject_instance_id": "Pulley_1", "object_instance_id": "Cable_1"}],
            "constraints": [],
        }
    ],
}
TARGET_RAW = {
    "metadata": {"publication_number": "US99999999B2", "title": "Target PSD tension device", "priority_date": "2020-01-01"},
    "source": {},
}
CANDIDATE_RAW = {
    "metadata": {"publication_number": "US12345678B2", "title": "Sliding door cable tensioner", "applicant": "Example", "priority_date": "2018-01-01", "publication_date": "2021-01-01"},
    "abstract": "A sliding door cable tensioner uses a pulley.",
    "description": "A spring biases a pulley toward a drive cable.",
    "claims": [{"claim_id": "C1", "claim_number": 1, "claim_type": "independent", "depends_on": [], "text": "A sliding door device comprising a cable and a tension pulley applying tension to the cable."}],
    "source": {"source_url": "https://patents.google.com/patent/US12345678B2/en"},
}


class FakeGemini:
    def __init__(self, api_key, model=None):
        self.model = model

    def generate_json(self, *, schema_name, **kwargs):
        if schema_name == "psd_related_candidate_fingerprints":
            return {
                "candidates": [
                    {
                        "publication_number": "US12345678B2",
                        "technology_ids": ["T2.6"],
                        "architecture_ids": [],
                        "problem_ids": ["P-FLX-01"],
                        "function_ids": ["F-FLX-09"],
                        "claim_element_ids": ["CE-CAB-001", "CE-PUL-004"],
                        "relation_ids": ["R-MOT-06"],
                        "solution_summary": "풀리가 케이블에 장력을 가해 처짐을 보상한다.",
                        "claim_focus": "케이블과 장력 풀리의 작동 관계가 핵심이다.",
                    }
                ]
            }
        return {
            "overview": "동일한 케이블 장력 문제를 다루는 특허를 선정했다.",
            "selection_method": "Ontology similarity",
            "related_patents": [
                {
                    "publication_number": "US12345678B2",
                    "selection_reason": "케이블 장력 문제와 장력 부여 관계가 공통이다.",
                    "shared_problem": "케이블의 장력 저하 또는 처짐을 억제하는 과제가 공통이다.",
                    "common_points": ["Drive Cable과 Tension Pulley를 사용한다."],
                    "differences": ["세부 장력 보상 구조가 다르다."],
                    "technical_development": "동일 과제를 다른 장력 보상 메커니즘으로 구현한 변형이다.",
                }
            ],
            "comparison_summary": "두 특허는 장력 안정화를 공통 목표로 하되 구현 구조가 다르다.",
        }


def test_module2_end_to_end_with_mocks(monkeypatch):
    monkeypatch.setattr(module2, "GeminiJsonClient", FakeGemini)
    monkeypatch.setattr(
        module2,
        "search_related_patents",
        lambda *args, **kwargs: ([{"publication_number": "US12345678B2", "title": "Sliding door cable tensioner", "assignee": "Example", "publication_date": "2021-01-01", "source_url": "https://patents.google.com/patent/US12345678B2/en", "best_search_rank": 0}], ["sliding door cable tension"]),
    )
    monkeypatch.setattr(module2, "retrieve_patent_by_number", lambda number: CANDIDATE_RAW)
    result = module2.analyze_related_patents(
        target_result={"structured_patent": TARGET_STRUCTURED, "raw_patent": TARGET_RAW},
        gemini_api_key="fake",
        gemini_model="gemini-test",
    )
    assert result["status"] == "completed"
    assert len(result["related_patents"]) == 1
    assert result["related_patents"][0]["publication_number"] == "US12345678B2"
    assert result["related_patents"][0]["score"] > 90
    assert "장력" in result["related_patents"][0]["selection_reason"]
