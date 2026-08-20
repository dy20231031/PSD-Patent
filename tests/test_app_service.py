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
