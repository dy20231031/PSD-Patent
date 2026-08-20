from engine.app_service import analyze_patent


def test_mvp_service_returns_all_modules():
    result = analyze_patent("JP7604988B2", None)
    assert result["patent_number"] == "JP7604988B2"
    assert result["module1"]
    assert result["module2"]
    assert result["module3"]
    assert result["evidence"]
