from engine.app_service import analyze_patent


def test_service_returns_placeholders_for_patent_number_only():
    result = analyze_patent("JP7604988B2", None)
    assert result["patent_number"] == "JP7604988B2"
    assert result["status"] == "Patent number retrieval not connected"
    assert result["raw_patent"] is None
    assert result["structured_patent"] is None
    assert result["module2"]
    assert result["module3"]
