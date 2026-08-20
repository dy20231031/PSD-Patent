from engine.analysis_models import ClaimOntologyExtraction, Module1Report


def test_structured_output_schemas_are_strict_objects():
    claim_schema = ClaimOntologyExtraction.model_json_schema()
    report_schema = Module1Report.model_json_schema()
    assert claim_schema["type"] == "object"
    assert claim_schema.get("additionalProperties") is False
    assert report_schema.get("additionalProperties") is False
