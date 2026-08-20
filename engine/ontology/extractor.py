from __future__ import annotations

import json
from typing import Any

from engine.analysis_models import (
    ClaimOntologyExtraction,
    Module1Report,
    ProblemEffectExtraction,
    TechnologyExtraction,
)
from engine.llm.openai_client import OpenAIJsonClient
from engine.ontology.mapper import normalize_ontology_extraction
from engine.ontology.prompt_context import (
    build_claim_knowledge_context,
    build_problem_effect_context,
    build_taxonomy_context,
)
from engine.patent.context_router import route_context


CLAIM_INSTRUCTIONS = """
You are a patent claim analyst specialized in automotive Power Sliding Door (PSD) systems.
Extract the claim structure using ONLY the provided patent text and ONLY the provided controlled vocabularies.

Rules:
1. Claim facts must be grounded in the claim text. Use evidence_level E1 for explicit wording and E2 only for claim-internal entailment from grammar/antecedents. Never use domain knowledge to invent a claim fact.
2. Preserve original_expression and a short evidence_text from the claim.
3. First/second are instances, not new canonical master concepts. Position terms are attributes unless they truly define a distinct structure.
4. If no vocabulary entry is semantically suitable, set the canonical ID/name to null and normalization_status='unmapped_candidate'. Never force a nearest concept.
5. Relation direction must follow the canonical relation vocabulary. Use object_set for N-ary located_between when needed.
6. Functions describe what an element does; relations describe interactions between instances. Do not mix them.
7. State is not a claim-element attribute. Store state/mode separately.
8. Constraints preserve property/comparison/threshold/range/conditional/state/cardinality/alternative/sequence/negative/context/transformation limitations.
9. For dependent claims, extract ONLY limitations added beyond the parent claim. Do not restate the full parent claim.
10. plain_summary must be concise Korean, technically accurate, and not add facts beyond the claim.
""".strip()


PROBLEM_EFFECT_INSTRUCTIONS = """
You are a PSD patent specification analyst.
Extract technical problems and technical effects using ONLY the provided patent text and the controlled vocabularies.

Rules:
1. Problem is an undesirable technical condition, not merely a cause and not an effect.
2. Effect is the technical result produced by the disclosed invention, not a design attribute label by itself.
3. Do not reverse-infer a problem from an effect or an effect from a problem.
4. Use PE1/PE2/PE3 for problems and EE1/EE2/EE3 for effects. Do not output PE4/EE4 domain inference as patent fact.
5. Keep short evidence_text and exact source_section (Abstract/Background/Summary/Description).
6. If no controlled term fits, keep ID/name null and normalization_status='unmapped_candidate'.
7. primary/secondary role is for report readability only; multiple assertions are allowed.
""".strip()


TECHNOLOGY_INSTRUCTIONS = """
You are classifying a PSD patent into the provided PSD Core Taxonomy and Architecture & Structural Strategy Axis.
Use the normalized claim/problem/effect analysis as the primary evidence.

Rules:
1. Technology is multi-label. Choose one primary technology only for display; secondary labels are allowed.
2. Architecture is separate from technology and should be assigned only when the mounting/integration/unit strategy is supported.
3. Do not classify merely because a generic component appears. Classify the inventive technical mechanism.
4. Use only IDs/names from the provided catalogs; otherwise return null.
5. rationale must be concise Korean and tied to the structured patent facts.
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
9. evidence_note should remind the reader that detailed source excerpts are available in the Evidence tab.
""".strip()


def _schema(model_cls) -> dict[str, Any]:
    return model_cls.model_json_schema()


def _compact_structured_for_technology(structured_partial: dict) -> str:
    compact = {
        "independent_claims": [
            {
                "claim_id": c.get("claim_id"),
                "plain_summary": c.get("plain_summary"),
                "elements": [
                    {"id": e.get("master_element_id"), "name": e.get("canonical_name"), "original": e.get("original_expression")}
                    for e in c.get("claim_elements", [])
                ],
                "relations": [
                    {
                        "relation": r.get("canonical_relation"),
                        "subject": r.get("subject_instance_id"),
                        "object": r.get("object_instance_id"),
                        "object_set": r.get("object_set", []),
                    }
                    for r in c.get("relation_assertions", [])
                ],
                "functions": [f.get("canonical_function") for f in c.get("function_assignments", [])],
                "constraints": [x.get("normalized_expression") for x in c.get("constraints", [])],
            }
            for c in structured_partial.get("independent_claims", [])
        ],
        "problems": [
            {"id": x.get("problem_id"), "name": x.get("canonical_problem"), "evidence": x.get("evidence", {}).get("evidence_text")}
            for x in structured_partial.get("problem_assertions", [])
        ],
        "effects": [
            {"id": x.get("effect_id"), "name": x.get("canonical_effect"), "evidence": x.get("evidence", {}).get("evidence_text")}
            for x in structured_partial.get("effect_assertions", [])
        ],
    }
    return json.dumps(compact, ensure_ascii=False)


def extract_structured_patent(
    *,
    raw_patent: dict,
    knowledge_base: dict[str, dict],
    llm: OpenAIJsonClient,
) -> tuple[dict, dict[str, Any]]:
    """Run the v0.2 ontology extraction pipeline.

    Returns `(structured_patent, trace)` where trace records context sizes and
    provider/model metadata for debugging without storing secrets.
    """
    claim_context = route_context(raw_patent, "ontology_claims", max_chars=70000)
    problem_context = route_context(raw_patent, "problem_effect", max_chars=65000)

    claim_input = (
        "# Patent claim context\n" + claim_context["text"] +
        "\n\n# PSD controlled vocabulary catalog\n" + build_claim_knowledge_context(knowledge_base)
    )
    claim_data = llm.generate_json(
        instructions=CLAIM_INSTRUCTIONS,
        input_text=claim_input,
        schema_name="psd_claim_ontology_extraction",
        json_schema=_schema(ClaimOntologyExtraction),
    )
    claim_data = ClaimOntologyExtraction.model_validate(claim_data).model_dump()

    problem_input = (
        "# Patent specification context\n" + problem_context["text"] +
        "\n\n# PSD Problem / Effect controlled vocabulary\n" + build_problem_effect_context(knowledge_base)
    )
    pe_data = llm.generate_json(
        instructions=PROBLEM_EFFECT_INSTRUCTIONS,
        input_text=problem_input,
        schema_name="psd_problem_effect_extraction",
        json_schema=_schema(ProblemEffectExtraction),
    )
    pe_data = ProblemEffectExtraction.model_validate(pe_data).model_dump()

    partial = {
        "independent_claims": claim_data["independent_claims"],
        "dependent_claims": claim_data["dependent_claims"],
        "problem_assertions": pe_data["problems"],
        "effect_assertions": pe_data["effects"],
    }
    technology_input = (
        "# Normalized patent facts (pre-validation)\n" + _compact_structured_for_technology(partial) +
        "\n\n# PSD taxonomy catalog\n" + build_taxonomy_context(knowledge_base)
    )
    tech_data = llm.generate_json(
        instructions=TECHNOLOGY_INSTRUCTIONS,
        input_text=technology_input,
        schema_name="psd_technology_assignment",
        json_schema=_schema(TechnologyExtraction),
    )
    tech_data = TechnologyExtraction.model_validate(tech_data).model_dump()

    normalized, warnings = normalize_ontology_extraction(
        claim_extraction=claim_data,
        problem_effect=pe_data,
        technology=tech_data,
        knowledge_base=knowledge_base,
    )
    normalized["patent"] = {
        "publication_number": raw_patent.get("metadata", {}).get("publication_number"),
        "title": raw_patent.get("metadata", {}).get("title"),
        "applicant": raw_patent.get("metadata", {}).get("applicant"),
        "source_file": raw_patent.get("metadata", {}).get("filename"),
    }

    trace = {
        "model": llm.model,
        "claim_context": {k: v for k, v in claim_context.items() if k != "text"},
        "problem_effect_context": {k: v for k, v in problem_context.items() if k != "text"},
        "normalization_warning_count": len(warnings),
    }
    normalized["analysis_trace"] = trace
    return normalized, trace


def generate_module1_report(*, structured_patent: dict, llm: OpenAIJsonClient) -> dict:
    report_input = json.dumps(structured_patent, ensure_ascii=False)
    data = llm.generate_json(
        instructions=REPORT_INSTRUCTIONS,
        input_text="# Structured Patent Analysis\n" + report_input,
        schema_name="psd_module1_explanation_report",
        json_schema=_schema(Module1Report),
    )
    return Module1Report.model_validate(data).model_dump()
