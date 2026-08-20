from engine.reports.figures import select_representative_figures


def test_select_representative_figures_prefers_matching_caption_and_overview():
    result = {
        "primary_technology": "Tension Slack Management",
        "module1_report": {
            "core_problem": "cable tension loss",
            "core_technology_summary": "spring loaded tension pulley maintains cable tension",
            "operation_principle_steps": [],
            "independent_claims": [{
                "plain_explanation": "A tension pulley applies tension to a drive cable",
                "relation_explanation": "spring biases pulley",
                "claim_elements": [{"name": "Tension Pulley", "original_expression": "pulley"}],
            }],
        },
        "raw_patent": {"figures": [
            {"figure_number": 1, "label": "FIG. 1", "image_url": "u1", "caption": "overall vehicle arrangement"},
            {"figure_number": 2, "label": "FIG. 2", "image_url": "u2", "caption": "spring loaded tension pulley and drive cable"},
            {"figure_number": 3, "label": "FIG. 3", "image_url": "u3", "caption": "electrical connector"},
        ]},
    }
    selected = select_representative_figures(result, limit=2)
    assert selected[0]["figure_number"] == 2
    assert len(selected) == 2
