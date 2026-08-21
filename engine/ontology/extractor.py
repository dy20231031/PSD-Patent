from __future__ import annotations

import json
from typing import Any

from engine.analysis_models import IntegratedPatentExtraction, Module1Report
from engine.llm.gemini_client import GeminiJsonClient, LLMResponseError
from engine.ontology.mapper import normalize_ontology_extraction
from engine.ontology.prompt_context import (
    build_claim_knowledge_context,
    build_problem_effect_context,
    build_taxonomy_context,
)
from engine.patent.context_router import route_context


INTEGRATED_EXTRACTION_INSTRUCTIONS = """
You are a patent analyst specialized in automotive Power Sliding Door (PSD) systems.
Perform ONE integrated structured analysis using ONLY the supplied patent contexts and ONLY the supplied controlled vocabularies.

The output has six distinct sections. Complete them in this priority order:
PRIORITY 1 — independent/dependent claim structure: Claim Elements, Relations, Functions, States/Modes, Constraints.
PRIORITY 2 — specification-supported Problems and Effects.
PRIORITY 3 — PSD Technology and Architecture classification based on the inventive mechanism established above.

A. CLAIM ANALYSIS RULES
1. Claim facts must be grounded in the supplied claim text. Use evidence_level E1 for explicit wording and E2 only for claim-internal entailment from grammar/antecedents. Never use domain knowledge to invent a claim fact.
2. Preserve original_expression and a short evidence_text from the claim.
3. First/second are instances, not new canonical master concepts. Position terms are attributes unless they truly define a distinct structure.
4. If no vocabulary entry is semantically suitable, set the canonical ID/name to null and normalization_status='unmapped_candidate'. Never force a nearest concept.
5. Relation direction must follow the canonical relation vocabulary. Use object_set for N-ary located_between when needed.
6. Functions describe what an element does; relations describe interactions between instances. Do not mix them.
7. State is not a claim-element attribute. Store state/mode separately.
8. Constraints preserve property/comparison/threshold/range/conditional/state/cardinality/alternative/sequence/negative/context/transformation limitations.
9. For dependent claims, extract ONLY limitations added beyond the parent claim. Do not restate the full parent claim.
10. plain_summary must be concise Korean, technically accurate, and not add facts beyond the claim.
11. Do not omit a claim-required element or relation merely to make the output shorter. Claim completeness has priority over every other section.

B. PROBLEM / EFFECT RULES
1. Problem is an undesirable technical condition, not merely a cause and not an effect.
2. Effect is the technical result produced by the disclosed invention, not a design attribute label by itself.
3. Do not reverse-infer a problem from an effect or an effect from a problem.
4. Use PE1/PE2/PE3 for problems and EE1/EE2/EE3 for effects. Do not output PE4/EE4 domain inference as patent fact.
5. Keep short evidence_text and exact source_section (Abstract/Background/Summary/Description).
6. If no controlled term fits, keep ID/name null and normalization_status='unmapped_candidate'.
7. primary/secondary role is for report readability only; multiple assertions are allowed.

C. TECHNOLOGY / ARCHITECTURE RULES
1. Technology is multi-label. Choose one primary technology only for display; secondary labels are allowed.
2. Architecture is separate from technology and should be assigned only when the mounting/integration/unit strategy is supported.
3. Classify the inventive mechanism established by the claim/problem/effect facts in THIS SAME analysis; do not classify merely because a generic component appears.
4. Use only IDs/names from the provided catalogs; otherwise return null.
5. rationale must be concise Korean and tied to the extracted structured patent facts.

D. CROSS-SECTION CONSISTENCY
1. Technology classification must be consistent with the extracted claim mechanism, not an independent guess.
2. Problems/effects may come from specification text, but must not be used to add unclaimed structures to claim analysis.
3. Every evidence_text must appear in the corresponding supplied context. Never fabricate quotations.
""".strip()


REPORT_INSTRUCTIONS = """
You are writing an engineering-oriented Korean patent explanation report for a reader who wants to understand the invention, not memorize ontology IDs.
Use ONLY the supplied normalized Structured Patent Analysis. Do not re-read or independently reinterpret the original patent and do not add unsupported facts.

Writing principles:
1. Do NOT expose internal IDs such as CE-..., P-..., E-..., T2.6 unless absolutely necessary. Use readable technical names.
2. Keep important patent terms (Motor, Drum, Drive Cable, Guide Pulley, Cinching Mechanism, etc.) and explain them naturally on first use.
3. Explain 'what problem -> what structure/relationship -> how it works -> what effect' as a causal story.
4. Distinguish claim-required limitations from description-supported problem/effect statements.
5. Explain independent claims in plain Korean while preserving legal/technical limitations. Do not give infringement/legal conclusions.
6. For operation principle, use ordered steps derived from normalized functions/relations/states. If the structured data does not support a step, omit it.
7. If something is not identified, say that it was not clearly identified rather than guessing.
8. scope_note should highlight what appears to be a required structural/relational/constraint condition in that claim, without legal advice.
9. evidence_note should remind the reader that detailed source excerpts are available in the Evidence section.
""".strip()


def _schema(model_cls) -> dict[str, Any]:
    return model_cls.model_json_schema()


def extract_structured_patent(
    *,
    raw_patent: dict,
    knowledge_base: dict[str, dict],
    llm: GeminiJsonClient,
) -> tuple[dict, dict[str, Any]]:
    """Module 1 integrated extraction pipeline: one Gemini call before report.

    Legacy v0.6 used three extraction calls (claims, problem/effect, technology).
    This version routes the same task-specific contexts but asks one structured
    response to populate all sections. Canonical normalization and validation
    remain deterministic and unchanged.
    """
    claim_context = route_context(raw_patent, "ontology_claims", max_chars=70000)
    problem_context = route_context(raw_patent, "problem_effect", max_chars=65000)

    integrated_input = (
        "# A. Patent claim context — highest priority\n"
        + claim_context["text"]
        + "\n\n# B. Patent specification context — problems/effects only\n"
        + problem_context["text"]
        + "\n\n# C. PSD claim controlled vocabularies\n"
        + build_claim_knowledge_context(knowledge_base)
        + "\n\n# D. PSD Problem / Effect controlled vocabularies\n"
        + build_problem_effect_context(knowledge_base)
        + "\n\n# E. PSD Technology / Architecture taxonomy\n"
        + build_taxonomy_context(knowledge_base)
    )

    integrated_data = llm.generate_json(
        instructions=INTEGRATED_EXTRACTION_INSTRUCTIONS,
        input_text=integrated_input,
        schema_name="psd_integrated_patent_extraction",
        json_schema=_schema(IntegratedPatentExtraction),
    )
    integrated = IntegratedPatentExtraction.model_validate(integrated_data).model_dump()

    raw_independent = [c for c in raw_patent.get("claims", []) if c.get("claim_type") == "independent"]
    if raw_independent and not integrated.get("independent_claims"):
        # Protect report quality: one-call consolidation must never turn a parsed
        # independent claim into an empty claim analysis merely to save quota.
        raise LLMResponseError(
            "통합 Ontology Extraction이 파싱된 독립청구항을 구조화하지 못했습니다. "
            "불완전한 보고서 생성을 중단합니다."
        )

    # Split the integrated response back into the legacy contracts so the frozen
    # ontology normalizer/validator remains exactly the same code path.
    claim_data = {
        "independent_claims": integrated["independent_claims"],
        "dependent_claims": integrated["dependent_claims"],
    }
    pe_data = {
        "problems": integrated["problems"],
        "effects": integrated["effects"],
    }
    tech_data = {
        "technology_assignments": integrated["technology_assignments"],
        "architecture_assignments": integrated["architecture_assignments"],
    }

    normalized, warnings = normalize_ontology_extraction(
        claim_extraction=claim_data,
        problem_effect=pe_data,
        technology=tech_data,
        knowledge_base=knowledge_base,
    )
    if len(integrated.get("independent_claims", [])) != len(raw_independent):
        warning = (
            "INDEPENDENT_CLAIM_COUNT_MISMATCH: "
            f"parsed={len(raw_independent)}, extracted={len(integrated.get('independent_claims', []))}"
        )
        warnings.append(warning)
        normalized.setdefault("validation_warnings", []).append(warning)
    normalized["patent"] = {
        "publication_number": raw_patent.get("metadata", {}).get("publication_number"),
        "title": raw_patent.get("metadata", {}).get("title"),
        "applicant": raw_patent.get("metadata", {}).get("applicant"),
        "source_file": raw_patent.get("metadata", {}).get("filename"),
        "source_url": raw_patent.get("source", {}).get("source_url"),
    }

    trace = {
        "model": llm.model,
        "pipeline": "integrated_2_call_module1",
        "module1_expected_llm_calls": 2,
        "extraction_llm_calls": 1,
        "claim_context": {k: v for k, v in claim_context.items() if k != "text"},
        "problem_effect_context": {k: v for k, v in problem_context.items() if k != "text"},
        "normalization_warning_count": len(warnings),
    }
    normalized["analysis_trace"] = trace
    return normalized, trace


def generate_module1_report(*, structured_patent: dict, llm: GeminiJsonClient) -> dict:
    """Second and final Gemini call for Module 1: explanation only."""
    report_input = json.dumps(structured_patent, ensure_ascii=False)
    data = llm.generate_json(
        instructions=REPORT_INSTRUCTIONS,
        input_text="# Structured Patent Analysis\n" + report_input,
        schema_name="psd_module1_explanation_report",
        json_schema=_schema(Module1Report),
    )
    return Module1Report.model_validate(data).model_dump()
