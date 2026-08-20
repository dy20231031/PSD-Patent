from engine.patent.context_router import route_context
from engine.patent.parser import parse_patent_text
from tests.test_patent_parser import SAMPLE_PATENT_TEXT


def test_context_router_selects_claims_and_problem_sections():
    parsed = parse_patent_text(SAMPLE_PATENT_TEXT)
    claims = route_context(parsed, "ontology_claims")
    assert "Independent Claims" in claims["text"]
    assert "Claim 1" in claims["text"]
    assert "Dependent Claims" in claims["text"]
    assert "Claim 2" in claims["text"]

    problem = route_context(parsed, "problem_effect")
    assert "## Background" in problem["text"]
    assert "develop slack" in problem["text"]
    assert "## Summary" in problem["text"]
