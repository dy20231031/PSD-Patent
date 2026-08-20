from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from typing import Any

from engine.analysis_models import CandidateBatchExtraction, Module2Report
from engine.llm.gemini_client import GeminiJsonClient, LLMResponseError
from engine.ontology.loader import load_all_knowledge
from engine.patent.retriever import PatentRetrievalError, retrieve_patent_by_number
from engine.retrieval.patent_search import RelatedPatentSearchError, search_related_patents
from engine.retrieval.reranker import DEFAULT_WEIGHTS, build_target_fingerprint, rerank_candidates


CANDIDATE_INSTRUCTIONS = """
You are performing lightweight ontology fingerprinting for related automotive Power Sliding Door (PSD) patents.
For EACH candidate patent, use only its supplied abstract/claims/description excerpt and ONLY the supplied controlled-vocabulary IDs.

Rules:
1. Return one candidate entry per supplied publication_number whenever there is enough text to analyze it.
2. Use only exact catalog IDs. If a concept is not clearly supported, omit it; never invent an ID.
3. technology_ids and architecture_ids classify the inventive mechanism/architecture, not generic components.
4. problem_ids are only technical problems stated or directly supported by the supplied text. Do not reverse-infer from effects.
5. function_ids, claim_element_ids and relation_ids should primarily reflect independent-claim facts.
6. solution_summary: 1-2 concise Korean sentences explaining the candidate's solution mechanism.
7. claim_focus: one concise Korean sentence describing the independent claim's main structural/relational focus.
8. Classify psd_relevance as exactly high, medium, or low. high = explicitly automotive/vehicle power sliding door or its direct drive/guide/latch subsystem; medium = generic sliding-door technology strongly transferable to PSD; low = unrelated domains such as elevators, building doors, windows/sunroofs, liftgates only, or generic machinery without a sliding-door connection.
9. psd_relevance_reason: one concise Korean sentence grounded in the supplied candidate text.
10. Do not make infringement, novelty or legal-scope conclusions.
""".strip()


COMPARISON_INSTRUCTIONS = """
You are writing Module 2 of an engineering-oriented PSD patent intelligence report.
Compare the target patent with the supplied top related patents using ONLY the supplied normalized target facts, candidate ontology fingerprints, abstracts/claim excerpts, and computed similarity scores.

Rules:
1. Write in clear Korean for an engineer who wants to understand why the patents are related and how their solutions differ.
2. Do not expose internal ontology IDs in prose.
3. selection_reason should explain the strongest technical reasons for relevance (problem/function/claim structure/technology).
4. shared_problem must not invent a common problem; if not explicitly supported, say the common problem is not clearly established and explain the nearest shared technical objective.
5. common_points and differences should focus on concrete structures, relations, functions and claim conditions.
6. technical_development describes an observed technical variation/evolution. Do not claim superiority or novelty unless the supplied facts support it.
7. Do not make infringement, validity, freedom-to-operate or legal conclusions.
8. Preserve each publication_number exactly so results can be joined back to source metadata.
""".strip()


def build_module2_placeholder() -> dict:
    return {
        "status": "not_run",
        "related_patents": [],
        "comparison_summary": "관련 특허 분석을 실행하면 공개 특허 후보를 검색하고 PSD Ontology 기준으로 비교합니다.",
    }


def _schema(model_cls) -> dict[str, Any]:
    return model_cls.model_json_schema()


def _truncate(text: str | None, n: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:n]


def _candidate_context(raw: dict, *, max_chars: int = 15000) -> dict[str, Any]:
    metadata = raw.get("metadata") or {}
    independent = [c for c in raw.get("claims", []) if c.get("claim_type") == "independent"]
    claim_text = "\n\n".join(
        f"Claim {c.get('claim_number')}: {c.get('text', '')}" for c in independent[:3]
    )
    description = raw.get("description") or ""
    payload = {
        "publication_number": metadata.get("publication_number"),
        "title": metadata.get("title"),
        "applicant": metadata.get("applicant"),
        "priority_date": metadata.get("priority_date"),
        "publication_date": metadata.get("publication_date"),
        "abstract": _truncate(raw.get("abstract"), 4200),
        "independent_claims": _truncate(claim_text, 8500),
        "description_excerpt": _truncate(description, 2500),
    }
    # Safety cap for unexpectedly verbose HTML extraction.
    encoded = json.dumps(payload, ensure_ascii=False)
    if len(encoded) > max_chars:
        payload["description_excerpt"] = ""
        payload["independent_claims"] = _truncate(claim_text, 6500)
    return payload


def _catalog_context(kb: dict[str, dict]) -> str:
    compact = {
        "technology": [
            {"id": x["id"], "name": x.get("name")}
            for x in kb["taxonomy"]["technology_nodes"]
        ],
        "architecture": [
            {"id": x["id"], "name": x.get("name")}
            for x in kb["taxonomy"]["architecture_values"]
        ],
        "problems": [
            {"id": x["id"], "name": x.get("canonical_name"), "ko": x.get("korean_name")}
            for x in kb["problems"]["items"]
        ],
        "functions": [
            {"id": x["id"], "name": x.get("canonical_name")}
            for x in kb["functions"]["items"]
        ],
        "claim_elements": [
            {"id": x["id"], "name": x.get("canonical_name")}
            for x in kb["claim_elements"]["items"]
        ],
        "relations": [
            {"id": x["id"], "name": x.get("canonical_name")}
            for x in kb["relations"]["items"]
        ],
    }
    return json.dumps(compact, ensure_ascii=False, separators=(",", ":"))


def _allowed_ids(kb: dict[str, dict]) -> dict[str, set[str]]:
    return {
        "technology_ids": {x["id"] for x in kb["taxonomy"]["technology_nodes"]},
        "architecture_ids": {x["id"] for x in kb["taxonomy"]["architecture_values"]},
        "problem_ids": {x["id"] for x in kb["problems"]["items"]},
        "function_ids": {x["id"] for x in kb["functions"]["items"]},
        "claim_element_ids": {x["id"] for x in kb["claim_elements"]["items"]},
        "relation_ids": {x["id"] for x in kb["relations"]["items"]},
    }


def _normalize_fingerprint(fp: dict, allowed: dict[str, set[str]]) -> tuple[dict, list[str]]:
    normalized = dict(fp)
    warnings: list[str] = []
    for field, allowed_values in allowed.items():
        values: list[str] = []
        for value in fp.get(field, []) or []:
            if value in allowed_values:
                if value not in values:
                    values.append(value)
            else:
                warnings.append(f"{fp.get('publication_number')}: unknown {field} value {value}")
        normalized[field] = values
    return normalized, warnings


def _same_family_likely(target_raw: dict, candidate_raw: dict) -> bool:
    tm = target_raw.get("metadata") or {}
    cm = candidate_raw.get("metadata") or {}
    if not tm or not cm:
        return False
    t_family = str(tm.get("family_id") or "").strip()
    c_family = str(cm.get("family_id") or "").strip()
    if t_family and c_family:
        return t_family == c_family
    t_priority = (tm.get("priority_date") or "")[:10]
    c_priority = (cm.get("priority_date") or "")[:10]
    if not t_priority or t_priority != c_priority:
        return False
    t_title = re.sub(r"\W+", " ", (tm.get("title") or "").lower()).strip()
    c_title = re.sub(r"\W+", " ", (cm.get("title") or "").lower()).strip()
    if not t_title or not c_title:
        return False
    return SequenceMatcher(None, t_title, c_title).ratio() >= 0.78


def _target_compact(structured: dict) -> dict[str, Any]:
    return {
        "patent": structured.get("patent") or {},
        "technology_assignments": structured.get("technology_assignments") or [],
        "architecture_assignments": structured.get("architecture_assignments") or [],
        "problems": [
            {
                "id": x.get("problem_id"),
                "name": x.get("canonical_problem") or x.get("korean_name"),
            }
            for x in structured.get("problem_assertions", [])
        ],
        "effects": [
            {"id": x.get("effect_id"), "name": x.get("canonical_effect") or x.get("korean_name")}
            for x in structured.get("effect_assertions", [])
        ],
        "independent_claims": [
            {
                "claim_number": c.get("claim_number"),
                "summary": c.get("plain_summary"),
                "elements": [e.get("canonical_name") for e in c.get("claim_elements", []) if e.get("canonical_name")],
                "functions": [f.get("canonical_function") for f in c.get("function_assignments", []) if f.get("canonical_function")],
                "relations": [
                    {
                        "relation": r.get("canonical_relation"),
                        "subject": r.get("subject_instance_id"),
                        "object": r.get("object_instance_id"),
                    }
                    for r in c.get("relation_assertions", []) if r.get("canonical_relation")
                ],
                "constraints": [x.get("normalized_expression") for x in c.get("constraints", []) if x.get("normalized_expression")],
            }
            for c in structured.get("independent_claims", [])
        ],
    }


def _name_maps(kb: dict[str, dict]) -> dict[str, dict[str, str]]:
    return {
        "technology_ids": {x["id"]: x.get("name") or x["id"] for x in kb["taxonomy"]["technology_nodes"]},
        "architecture_ids": {x["id"]: x.get("name") or x["id"] for x in kb["taxonomy"]["architecture_values"]},
        "problem_ids": {x["id"]: x.get("korean_name") or x.get("canonical_name") or x["id"] for x in kb["problems"]["items"]},
        "function_ids": {x["id"]: x.get("canonical_name") or x["id"] for x in kb["functions"]["items"]},
        "claim_element_ids": {x["id"]: x.get("canonical_name") or x["id"] for x in kb["claim_elements"]["items"]},
        "relation_ids": {x["id"]: x.get("canonical_name") or x["id"] for x in kb["relations"]["items"]},
    }


def _overlap_names(target_fp: dict, candidate_fp: dict, maps: dict[str, dict[str, str]], field: str) -> list[str]:
    common = set(target_fp.get(field, [])) & set(candidate_fp.get(field, []))
    return [maps[field].get(x, x) for x in sorted(common)]


def _fallback_report(top: list[dict], target_fp: dict, kb: dict[str, dict]) -> dict:
    maps = _name_maps(kb)
    rows: list[dict[str, Any]] = []
    for item in top:
        fp = item.get("fingerprint") or {}
        common_problem = _overlap_names(target_fp, fp, maps, "problem_ids")
        common_function = _overlap_names(target_fp, fp, maps, "function_ids")
        common_elements = _overlap_names(target_fp, fp, maps, "claim_element_ids")
        common_relations = _overlap_names(target_fp, fp, maps, "relation_ids")
        anchors = common_problem + common_function + common_relations + common_elements
        selection = "공통 Ontology 특징: " + ", ".join(anchors[:6]) if anchors else "PSD 기술영역과 검색 문맥의 관련성을 바탕으로 선정했습니다."
        rows.append(
            {
                "publication_number": item["publication_number"],
                "selection_reason": selection,
                "shared_problem": ("공통 문제: " + ", ".join(common_problem)) if common_problem else "공통 Problem ID는 명확히 일치하지 않았습니다.",
                "common_points": [
                    x for x in [
                        ("공통 기능: " + ", ".join(common_function)) if common_function else "",
                        ("공통 구성요소: " + ", ".join(common_elements)) if common_elements else "",
                        ("공통 관계: " + ", ".join(common_relations)) if common_relations else "",
                    ] if x
                ] or ["공통 구조는 제한적으로 확인되었습니다."],
                "differences": [item.get("fingerprint", {}).get("claim_focus") or "독립청구항의 구체 구조가 다릅니다."],
                "technical_development": item.get("fingerprint", {}).get("solution_summary") or "관련 구조의 기술적 변형으로 볼 수 있습니다.",
            }
        )
    return {
        "overview": "공개 특허 후보를 검색한 뒤 PSD Ontology 공통점을 기준으로 관련특허를 선정했습니다.",
        "selection_method": "Relation 25%, Problem 20%, Function 20%, Technology 15%, Claim Element 15%, Architecture 5%의 Ontology 유사도",
        "related_patents": rows,
        "comparison_summary": "관련 특허들은 동일하거나 인접한 PSD 기술과제를 서로 다른 구성·관계로 구현하는 사례를 중심으로 선정되었습니다.",
    }


def analyze_related_patents(
    *,
    target_result: dict,
    gemini_api_key: str,
    gemini_model: str = "gemini-3.7-flash",
    report_model: str | None = None,
    fallback_model: str | None = None,
    max_retries: int = 2,
    top_n: int = 5,
    max_candidate_analysis: int = 10,
) -> dict:
    """Run Module 2: search -> lightweight ontology fingerprint -> rerank -> compare."""
    structured = target_result.get("structured_patent")
    raw_target = target_result.get("raw_patent")
    if not structured or not raw_target:
        return {
            "status": "unavailable",
            "overview": "Module 1의 구조화 분석이 완료된 특허에서만 관련특허 분석을 실행할 수 있습니다.",
            "related_patents": [],
            "comparison_summary": "",
            "warnings": [],
        }
    if not gemini_api_key:
        return {
            "status": "llm_not_configured",
            "overview": "Gemini API 설정이 필요합니다.",
            "related_patents": [],
            "comparison_summary": "",
            "warnings": [],
        }

    kb = load_all_knowledge()
    target_fp = build_target_fingerprint(structured)
    warnings: list[str] = []

    try:
        search_candidates, queries = search_related_patents(
            structured,
            raw_target,
            per_query=10,
            max_candidates=24,
        )
    except RelatedPatentSearchError as exc:
        return {
            "status": "search_failed",
            "overview": str(exc),
            "search_queries": [],
            "related_patents": [],
            "comparison_summary": "",
            "warnings": [str(exc)],
        }

    # Retrieve only enough candidate documents for the lightweight ontology pass.
    detailed: list[dict[str, Any]] = []
    retrieval_failures = 0
    for candidate in search_candidates:
        if len(detailed) >= max_candidate_analysis:
            break
        try:
            raw = retrieve_patent_by_number(candidate["publication_number"])
        except PatentRetrievalError as exc:
            retrieval_failures += 1
            warnings.append(f"{candidate['publication_number']} 원문 조회 실패: {exc}")
            continue
        if _same_family_likely(raw_target, raw):
            warnings.append(f"{candidate['publication_number']}: 분석 대상과 동일 Patent Family로 제외")
            continue
        if any(_same_family_likely(existing.get("raw_patent") or {}, raw) for existing in detailed):
            warnings.append(f"{candidate['publication_number']}: 이미 확보한 후보와 동일 Patent Family로 중복 제외")
            continue
        independent_claims = [c for c in raw.get("claims", []) if c.get("claim_type") == "independent"]
        if not independent_claims:
            warnings.append(f"{candidate['publication_number']}: 독립청구항을 확인하지 못해 후보 분석에서 제외")
            continue
        detail = dict(candidate)
        detail["raw_patent"] = raw
        detail["comparison_context"] = _candidate_context(raw)
        detail["representative_figure"] = (raw.get("figures") or [None])[0]
        detailed.append(detail)

    if not detailed:
        return {
            "status": "no_candidates",
            "overview": "검색 후보는 있었지만 비교 가능한 청구항을 가진 관련 특허를 확보하지 못했습니다.",
            "search_queries": queries,
            "related_patents": [],
            "comparison_summary": "",
            "warnings": warnings,
        }

    llm = GeminiJsonClient(
        gemini_api_key,
        model=gemini_model,
        fallback_model=fallback_model,
        max_retries=max_retries,
    )
    candidate_input = {
        "candidate_patents": [x["comparison_context"] for x in detailed],
        "controlled_vocabularies": json.loads(_catalog_context(kb)),
    }
    try:
        fp_data = llm.generate_json(
            instructions=CANDIDATE_INSTRUCTIONS,
            input_text=json.dumps(candidate_input, ensure_ascii=False),
            schema_name="psd_related_candidate_fingerprints",
            json_schema=_schema(CandidateBatchExtraction),
        )
        fp_data = CandidateBatchExtraction.model_validate(fp_data).model_dump()
    except LLMResponseError as exc:
        return {
            "status": "candidate_analysis_failed",
            "overview": f"관련특허 후보의 Ontology 분석에 실패했습니다: {exc}",
            "search_queries": queries,
            "related_patents": [],
            "comparison_summary": "",
            "warnings": warnings + [str(exc)],
        }

    allowed = _allowed_ids(kb)
    fp_by_number: dict[str, dict] = {}
    for fp in fp_data.get("candidates", []):
        normalized, fp_warnings = _normalize_fingerprint(fp, allowed)
        warnings.extend(fp_warnings)
        relevance = str(normalized.get("psd_relevance") or "low").lower().strip()
        if relevance not in {"high", "medium", "low"}:
            relevance = "low"
            warnings.append(f"{normalized.get('publication_number')}: invalid PSD relevance normalized to low")
        normalized["psd_relevance"] = relevance
        if relevance == "low":
            warnings.append(f"{normalized.get('publication_number')}: PSD relevance low로 후보에서 제외")
            continue
        fp_by_number[normalized["publication_number"].upper()] = normalized

    scored_input: list[dict[str, Any]] = []
    for item in detailed:
        number = item["publication_number"].upper()
        fp = fp_by_number.get(number)
        if not fp:
            warnings.append(f"{number}: Gemini fingerprint 결과 누락")
            continue
        candidate_row = {k: v for k, v in item.items() if k not in {"raw_patent"}}
        candidate_row["fingerprint"] = fp
        scored_input.append(candidate_row)

    ranked = rerank_candidates(scored_input, target_fp, weights=DEFAULT_WEIGHTS)
    top = ranked[: max(1, min(top_n, 5))]
    if not top:
        return {
            "status": "no_ranked_candidates",
            "overview": "Ontology fingerprint를 생성했지만 관련도를 계산할 후보가 남지 않았습니다.",
            "search_queries": queries,
            "related_patents": [],
            "comparison_summary": "",
            "warnings": warnings,
        }

    report_llm = llm if not report_model or report_model == gemini_model else GeminiJsonClient(
        gemini_api_key,
        model=report_model,
        fallback_model=fallback_model,
        max_retries=max_retries,
    )
    comparison_payload = {
        "target_patent": _target_compact(structured),
        "selection_weights": DEFAULT_WEIGHTS,
        "top_candidates": [
            {
                "publication_number": x["publication_number"],
                "title": x.get("title"),
                "assignee": x.get("assignee"),
                "publication_date": x.get("publication_date"),
                "score": x.get("score"),
                "score_breakdown": x.get("score_breakdown"),
                "fingerprint": x.get("fingerprint"),
                "patent_excerpt": x.get("comparison_context"),
            }
            for x in top
        ],
    }
    try:
        report_data = report_llm.generate_json(
            instructions=COMPARISON_INSTRUCTIONS,
            input_text=json.dumps(comparison_payload, ensure_ascii=False),
            schema_name="psd_module2_related_patent_report",
            json_schema=_schema(Module2Report),
        )
        report = Module2Report.model_validate(report_data).model_dump()
        report_mode = "LLM explanation"
    except LLMResponseError as exc:
        report = _fallback_report(top, target_fp, kb)
        report_mode = f"deterministic fallback ({exc})"
        warnings.append(str(exc))

    narrative_by_number = {
        x["publication_number"].upper(): x for x in report.get("related_patents", [])
    }
    related_patents: list[dict[str, Any]] = []
    for item in top:
        number = item["publication_number"].upper()
        narrative = narrative_by_number.get(number, {})
        row = {
            "publication_number": number,
            "title": item.get("title") or (item.get("comparison_context") or {}).get("title") or "",
            "applicant": item.get("assignee") or (item.get("comparison_context") or {}).get("applicant") or "",
            "publication_date": item.get("publication_date") or (item.get("comparison_context") or {}).get("publication_date") or "",
            "source_url": item.get("source_url") or f"https://patents.google.com/patent/{number}/en",
            "score": item.get("score", 0.0),
            "relatedness_level": (
                "높음" if float(item.get("score", 0.0)) >= 60 else
                "중간" if float(item.get("score", 0.0)) >= 35 else "낮음"
            ),
            "score_breakdown": item.get("score_breakdown") or {},
            "psd_relevance": (item.get("fingerprint") or {}).get("psd_relevance") or "medium",
            "psd_relevance_reason": (item.get("fingerprint") or {}).get("psd_relevance_reason") or "",
            "representative_figure": item.get("representative_figure"),
            "solution_summary": (item.get("fingerprint") or {}).get("solution_summary") or "",
            "claim_focus": (item.get("fingerprint") or {}).get("claim_focus") or "",
            "selection_reason": narrative.get("selection_reason") or "",
            "shared_problem": narrative.get("shared_problem") or "",
            "common_points": narrative.get("common_points") or [],
            "differences": narrative.get("differences") or [],
            "technical_development": narrative.get("technical_development") or "",
        }
        related_patents.append(row)

    return {
        "status": "completed",
        "overview": report.get("overview") or "관련 공개 특허를 PSD Ontology 기준으로 비교했습니다.",
        "selection_method": report.get("selection_method") or "Ontology similarity",
        "comparison_summary": report.get("comparison_summary") or "",
        "search_queries": queries,
        "search_candidate_count": len(search_candidates),
        "analyzed_candidate_count": len(detailed),
        "retrieval_failure_count": retrieval_failures,
        "report_mode": report_mode,
        "related_patents": related_patents,
        "warnings": warnings,
    }
