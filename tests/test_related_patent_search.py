from engine.retrieval.patent_search import (
    build_related_search_queries,
    parse_google_patents_search_json,
)


STRUCTURED = {
    "technology_assignments": [{"technology_id": "T2.6", "technology_name": "Tension / Slack Management", "role": "primary"}],
    "problem_assertions": [{"problem_id": "P-FLX-01", "canonical_problem": "tension_loss_or_slack"}],
    "independent_claims": [
        {
            "claim_elements": [
                {"master_element_id": "CE-CAB-001", "canonical_name": "Drive Cable"},
                {"master_element_id": "CE-PUL-004", "canonical_name": "Tension Pulley"},
            ],
            "function_assignments": [{"function_id": "F-FLX-09", "canonical_function": "maintain_tension"}],
            "relation_assertions": [{"relation_id": "R-MOT-06", "canonical_relation": "applies_tension_to"}],
        }
    ],
}


def test_build_related_search_queries_uses_ontology_terms():
    queries = build_related_search_queries(STRUCTURED, {"metadata": {"title": "Power sliding door cable tensioner"}})
    joined = " ".join(queries).lower()
    assert "sliding door" in joined
    assert "tension" in joined
    assert "cable" in joined
    assert len(queries) <= 3


def test_parse_google_patents_xhr_search_json():
    payload = {
        "results": {
            "cluster": [
                {
                    "result": [
                        {
                            "rank": 0,
                            "patent": {
                                "publication_number": "US 12345678 B2",
                                "title": "<b>Power sliding door</b> cable tension device",
                                "snippet": "A pulley maintains cable tension.",
                                "assignee": "Example Corp",
                                "publication_date": "2024-05-01",
                            },
                        }
                    ]
                }
            ]
        }
    }
    rows = parse_google_patents_search_json(payload, query="sliding door cable")
    assert rows[0]["publication_number"] == "US12345678B2"
    assert rows[0]["title"] == "Power sliding door cable tension device"
    assert rows[0]["assignee"] == "Example Corp"
    assert rows[0]["source_url"].endswith("/US12345678B2/en")
