from engine.app_service import analyze_patent


RAW_RETRIEVED = {
    "schema_version": "raw-patent-v0.2",
    "source": {
        "input_type": "patent_number",
        "filename": None,
        "page_count": None,
        "text_char_count": 1000,
        "average_chars_per_page": None,
        "extraction_method": "google_patents_html",
        "ocr_used": False,
        "warnings": [],
        "source_url": "https://patents.google.com/patent/US10774572B2/en",
        "provider": "Google Patents",
    },
    "metadata": {
        "publication_number": "US10774572B2",
        "publication_number_raw": "US10774572B2",
        "title": "Opening-closing body driving device",
        "applicant": "Mitsuba Corp",
        "filename": None,
        "pdf_metadata": {},
        "application_number": None,
        "priority_date": None,
        "filing_date": None,
        "publication_date": None,
        "inventors": [],
        "legal_status": None,
    },
    "abstract": "Abstract",
    "background": "Background",
    "summary": "Summary",
    "figure_description": "",
    "description": "Description",
    "claims": [
        {"claim_id": "C1", "claim_number": 1, "claim_type": "independent", "depends_on": [], "text": "A device comprising a cable and pulley."}
    ],
    "parser_diagnostics": {
        "claim_count": 1,
        "independent_claim_count": 1,
        "dependent_claim_count": 0,
        "warnings": [],
    },
    "raw_text": "raw",
}


def test_service_retrieves_patent_number_without_pdf(monkeypatch):
    monkeypatch.setattr("engine.app_service.retrieve_patent_by_number", lambda number: RAW_RETRIEVED)
    result = analyze_patent("US10774572B2", None, gemini_api_key=None)
    assert result["patent_number"] == "US10774572B2"
    assert result["status"] == "Patent Parsed · LLM not configured"
    assert result["raw_patent"]["source"]["input_type"] == "patent_number"
    assert "공개 특허 원문 조회/파싱 완료" in result["overview"]


def test_service_blocks_claim_ontology_when_claims_zero(monkeypatch):
    empty = {**RAW_RETRIEVED, "claims": [], "parser_diagnostics": {"claim_count": 0, "independent_claim_count": 0, "dependent_claim_count": 0, "warnings": []}}
    monkeypatch.setattr("engine.app_service.retrieve_patent_by_number", lambda number: empty)
    result = analyze_patent("US10774572B2", None, gemini_api_key="fake")
    assert result["status"] == "Claim parsing failed"
    assert result["structured_patent"] is None
    assert result["module1_report"] is None


def test_successful_module1_result_is_cached(monkeypatch):
    from engine import app_service

    app_service.clear_analysis_cache()
    calls = {"retrieve": 0, "extract": 0, "report": 0}

    def fake_retrieve(number):
        calls["retrieve"] += 1
        return RAW_RETRIEVED

    class DummyClient:
        def __init__(self, api_key, model=None):
            self.model = model or "dummy"

    structured = {
        "independent_claims": [],
        "dependent_claims": [],
        "problem_assertions": [],
        "effect_assertions": [],
        "technology_assignments": [
            {"technology_id": "T2.6", "technology_name": "Tension / Slack Management", "role": "primary", "rationale": "test"}
        ],
        "architecture_assignments": [],
        "validation_warnings": [],
    }

    def fake_extract(**kwargs):
        calls["extract"] += 1
        return structured, {"pipeline": "integrated_2_call_module1", "model": "dummy"}

    def fake_report(**kwargs):
        calls["report"] += 1
        return {"three_line_summary": {}, "independent_claims": []}

    monkeypatch.setattr(app_service, "retrieve_patent_by_number", fake_retrieve)
    monkeypatch.setattr(app_service, "GeminiJsonClient", DummyClient)
    monkeypatch.setattr(app_service, "extract_structured_patent", fake_extract)
    monkeypatch.setattr(app_service, "generate_module1_report", fake_report)

    first = app_service.analyze_patent(
        "US10774572B2", None, gemini_api_key="fake", gemini_model="gemini-a", report_model="gemini-b"
    )
    second = app_service.analyze_patent(
        "US 10774572 B2", None, gemini_api_key="fake", gemini_model="gemini-a", report_model="gemini-b"
    )

    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert calls == {"retrieve": 1, "extract": 1, "report": 1}
    app_service.clear_analysis_cache()
