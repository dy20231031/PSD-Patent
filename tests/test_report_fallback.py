from engine.reports.generator import build_fallback_module1_report


def test_fallback_report_is_explanation_oriented():
    structured = {
        "independent_claims": [
            {
                "claim_number": 1,
                "plain_summary": "스프링과 장력 풀리로 케이블 장력을 유지하는 구조이다.",
                "claim_elements": [
                    {
                        "element_instance_id": "DriveCable_1",
                        "canonical_name": "Drive Cable",
                        "original_expression": "drive cable",
                    }
                ],
                "relation_assertions": [],
                "function_assignments": [],
                "constraints": [],
            }
        ],
        "dependent_claims": [],
        "problem_assertions": [],
        "effect_assertions": [],
        "technology_assignments": [],
    }
    report = build_fallback_module1_report(structured)
    assert "what_is_patent" in report["three_line_summary"]
    assert report["independent_claims"][0]["claim_elements"][0]["name"] == "Drive Cable"
