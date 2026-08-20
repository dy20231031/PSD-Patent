from __future__ import annotations

from typing import Any

from engine.llm.gemini_client import GeminiJsonClient, LLMResponseError
from engine.modules.module1 import build_module1_placeholder
from engine.modules.module2 import analyze_related_patents as _analyze_related_patents, build_module2_placeholder
from engine.modules.module3 import build_module3_placeholder
from engine.ontology.extractor import extract_structured_patent, generate_module1_report
from engine.ontology.loader import load_all_knowledge
from engine.patent.parser import PatentParseError, parse_patent_pdf
from engine.patent.retriever import retrieve_patent_by_number
from engine.reports.generator import build_fallback_module1_report


def _module1_with_parsed_basics(parsed: dict, fallback_id: str) -> dict:
    module1 = build_module1_placeholder(fallback_id)
    metadata = parsed.get("metadata", {})
    claims = parsed.get("claims", [])
    module1["basic_info"] = {
        "publication_number": metadata.get("publication_number") or fallback_id,
        "title": metadata.get("title") or "자동 추출되지 않음",
        "applicant": metadata.get("applicant") or "자동 추출되지 않음",
        "source_file": metadata.get("filename") or "-",
        "claim_count": len(claims),
    }
    return module1


def _collect_evidence(structured: dict) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    def add(label: str, evidence: dict | None, canonical: str | None = None) -> None:
        if not evidence or not evidence.get("evidence_text"):
            return
        source = evidence.get("source_section") or evidence.get("claim_id") or "Patent"
        items.append(
            {
                "label": label,
                "canonical": canonical,
                "source": source,
                "claim_id": evidence.get("claim_id"),
                "evidence_level": evidence.get("evidence_level"),
                "text": evidence.get("evidence_text"),
            }
        )

    for claim in structured.get("independent_claims", []):
        for e in claim.get("claim_elements", []):
            add("Claim Element", e.get("evidence"), e.get("canonical_name") or e.get("original_expression"))
        for r in claim.get("relation_assertions", []):
            add("Relation", r.get("evidence"), r.get("canonical_relation"))
        for f in claim.get("function_assignments", []):
            add("Function", f.get("evidence"), f.get("canonical_function"))
        for c in claim.get("constraints", []):
            add("Claim Constraint", c.get("evidence"), c.get("canonical_constraint_type"))
        for s in claim.get("state_assertions", []):
            add("State", s.get("evidence"), s.get("state_dimension"))
        for m in claim.get("mode_assertions", []):
            add("Operation Mode", m.get("evidence"), m.get("canonical_mode"))

    for p in structured.get("problem_assertions", []):
        add("Problem", p.get("evidence"), p.get("canonical_problem"))
    for e in structured.get("effect_assertions", []):
        add("Effect", e.get("evidence"), e.get("canonical_effect"))

    seen: set[tuple] = set()
    deduped = []
    for item in items:
        key = (item["label"], item.get("canonical"), item.get("claim_id"), item["text"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def analyze_patent(
    patent_number: str | None,
    uploaded_file_name: str | None,
    uploaded_file_bytes: bytes | None = None,
    *,
    gemini_api_key: str | None = None,
    gemini_model: str = "gemini-3.7-flash",
    report_model: str | None = None,
) -> dict:
    """Patent number/PDF -> Raw Patent -> Ontology -> Module 1 service entry point.

    Patent-number input retrieves the public Google Patents page; PDF input uses
    embedded-text parsing. With Gemini configured, the service maps the parsed
    patent to the frozen PSD vocabulary and generates an explanation report.
    """
    display_id = patent_number or uploaded_file_name or "Uploaded Patent"

    # PDF takes precedence when both inputs are supplied; otherwise retrieve the
    # public patent page directly from the publication/grant number.
    if uploaded_file_bytes is not None:
        try:
            raw_patent = parse_patent_pdf(
                uploaded_file_bytes,
                filename=uploaded_file_name,
                patent_number_hint=patent_number,
            )
        except PatentParseError:
            raise
        except Exception as exc:
            raise PatentParseError(f"PDF 파싱 중 예상하지 못한 오류가 발생했습니다: {exc}") from exc
    elif patent_number:
        raw_patent = retrieve_patent_by_number(patent_number)
    else:
        raise PatentParseError("특허번호를 입력하거나 PDF를 업로드해 주세요.")

    metadata = raw_patent.get("metadata", {})
    parsed_id = metadata.get("publication_number") or display_id
    source = raw_patent.get("source", {})
    diagnostics = raw_patent.get("parser_diagnostics", {})
    input_type = source.get("input_type")
    if input_type == "patent_number":
        parser_overview = (
            f"공개 특허 원문 조회/파싱 완료: {source.get('provider') or 'Public patent source'}, "
            f"{source.get('text_char_count') or 0:,} characters, claims {diagnostics.get('claim_count', 0)}개."
        )
    else:
        parser_overview = (
            f"PDF 파싱 완료: {source.get('page_count') or '-'} pages, "
            f"{source.get('text_char_count') or 0:,} characters, claims {diagnostics.get('claim_count', 0)}개."
        )

    if diagnostics.get("claim_count", 0) == 0:
        return {
            "title": f"{parsed_id} · PSD Patent Analysis",
            "patent_number": parsed_id,
            "primary_technology": "Claim analysis unavailable",
            "status": "Claim parsing failed",
            "overview": (
                parser_overview
                + " 청구항을 식별하지 못해 Claim Element/Relation/Constraint 기반 Ontology 분석과 Module 1 전체 보고서는 실행하지 않았습니다. "
                + "Raw Patent JSON의 Parser Diagnostics를 확인하거나 다른 PDF/특허번호 입력을 사용해 주세요."
            ),
            "raw_patent": raw_patent,
            "structured_patent": None,
            "module1_report": None,
            "module1": _module1_with_parsed_basics(raw_patent, parsed_id),
            "module2": build_module2_placeholder(),
            "module3": build_module3_placeholder(),
            "evidence": [],
            "analysis_error": None,
        }

    if not gemini_api_key:
        return {
            "title": f"{parsed_id} · PSD Patent Analysis",
            "patent_number": parsed_id,
            "primary_technology": "Ontology analysis requires API key",
            "status": "Patent Parsed · LLM not configured",
            "overview": parser_overview + " Gemini API Key를 Streamlit Secrets에 설정하면 Ontology 분석과 Module 1 설명 보고서가 활성화됩니다.",
            "raw_patent": raw_patent,
            "structured_patent": None,
            "module1_report": None,
            "module1": _module1_with_parsed_basics(raw_patent, parsed_id),
            "module2": build_module2_placeholder(),
            "module3": build_module3_placeholder(),
            "evidence": [
                {
                    "label": "Parser source",
                    "canonical": None,
                    "source": source.get("source_url") or uploaded_file_name or "Parsed patent",
                    "claim_id": None,
                    "evidence_level": None,
                    "text": "특허 원문 파싱은 완료됐지만 LLM Ontology Extraction은 API Key가 없어 실행되지 않았습니다.",
                }
            ],
            "analysis_error": None,
        }

    llm = GeminiJsonClient(gemini_api_key, model=gemini_model)
    kb = load_all_knowledge()
    try:
        structured, trace = extract_structured_patent(raw_patent=raw_patent, knowledge_base=kb, llm=llm)
        report_llm = llm if not report_model or report_model == gemini_model else GeminiJsonClient(gemini_api_key, model=report_model)
        try:
            module1_report = generate_module1_report(structured_patent=structured, llm=report_llm)
            report_mode = "LLM explanation"
        except LLMResponseError as report_exc:
            module1_report = build_fallback_module1_report(structured)
            report_mode = f"deterministic fallback ({report_exc})"

        primary = next(
            (x for x in structured.get("technology_assignments", []) if x.get("role") == "primary" and x.get("technology_name")),
            None,
        )
        if primary is None:
            primary = next((x for x in structured.get("technology_assignments", []) if x.get("technology_name")), None)
        primary_technology = primary.get("technology_name") if primary else "분류 미확정"

        return {
            "title": f"{parsed_id} · PSD Patent Analysis",
            "patent_number": parsed_id,
            "primary_technology": primary_technology,
            "status": "Module 1 analyzed",
            "overview": (
                parser_overview
                + f" Ontology Extraction 및 Canonical normalization 완료. "
                f"검증 경고 {len(structured.get('validation_warnings', []))}개. Report mode: {report_mode}."
            ),
            "raw_patent": raw_patent,
            "structured_patent": structured,
            "module1_report": module1_report,
            "module1": _module1_with_parsed_basics(raw_patent, parsed_id),
            "module2": build_module2_placeholder(),
            "module3": build_module3_placeholder(),
            "evidence": _collect_evidence(structured),
            "analysis_trace": trace,
            "analysis_error": None,
        }
    except LLMResponseError as exc:
        return {
            "title": f"{parsed_id} · PSD Patent Analysis",
            "patent_number": parsed_id,
            "primary_technology": "Ontology analysis failed",
            "status": "Patent Parsed · LLM error",
            "overview": parser_overview + " Ontology 분석 중 LLM 오류가 발생했습니다. Raw Patent JSON은 정상적으로 사용할 수 있습니다.",
            "raw_patent": raw_patent,
            "structured_patent": None,
            "module1_report": None,
            "module1": _module1_with_parsed_basics(raw_patent, parsed_id),
            "module2": build_module2_placeholder(),
            "module3": build_module3_placeholder(),
            "evidence": [],
            "analysis_error": str(exc),
        }


def analyze_related_patents(
    target_result: dict,
    *,
    gemini_api_key: str | None,
    gemini_model: str = "gemini-3.7-flash",
    report_model: str | None = None,
    top_n: int = 5,
) -> dict:
    """Module 2 public service entry point.

    Requires a completed Module 1 structured patent. The search step is broad;
    final ranking uses the frozen PSD Ontology feature overlap.
    """
    return _analyze_related_patents(
        target_result=target_result,
        gemini_api_key=gemini_api_key or "",
        gemini_model=gemini_model,
        report_model=report_model,
        top_n=top_n,
    )
