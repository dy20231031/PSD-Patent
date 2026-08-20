from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KeyValue(StrictModel):
    key: str
    value: str


class EvidenceRef(StrictModel):
    source_section: str
    claim_id: str | None
    evidence_text: str
    evidence_level: str


class ClaimElementAnalysis(StrictModel):
    element_instance_id: str
    master_element_id: str | None
    canonical_name: str | None
    original_expression: str
    element_type: str | None
    instance_index: int | None
    role: str | None
    position: str | None
    attributes: list[KeyValue]
    normalization_status: str
    evidence: EvidenceRef


class RelationAnalysis(StrictModel):
    relation_assertion_id: str
    subject_instance_id: str
    relation_id: str | None
    canonical_relation: str | None
    object_instance_id: str | None
    object_set: list[str]
    attributes: list[KeyValue]
    normalization_status: str
    evidence: EvidenceRef


class FunctionAnalysis(StrictModel):
    function_assignment_id: str
    subject_instance_id: str
    function_id: str | None
    canonical_function: str | None
    target_instance_id: str | None
    normalization_status: str
    evidence: EvidenceRef


class StateAnalysis(StrictModel):
    state_assertion_id: str
    entity_instance_id: str
    state_dimension_id: str | None
    state_dimension: str | None
    state_value: str
    normalization_status: str
    evidence: EvidenceRef


class ModeAnalysis(StrictModel):
    mode_assertion_id: str
    mode_id: str | None
    canonical_mode: str | None
    normalization_status: str
    evidence: EvidenceRef


class ConstraintAnalysis(StrictModel):
    constraint_id: str
    constraint_type_id: str | None
    canonical_constraint_type: str | None
    normalized_expression: str
    referenced_instance_ids: list[str]
    operator: str | None
    context: list[KeyValue]
    normalization_status: str
    evidence: EvidenceRef


class IndependentClaimAnalysis(StrictModel):
    claim_id: str
    claim_number: int
    plain_summary: str
    claim_elements: list[ClaimElementAnalysis]
    relation_assertions: list[RelationAnalysis]
    function_assignments: list[FunctionAnalysis]
    state_assertions: list[StateAnalysis]
    mode_assertions: list[ModeAnalysis]
    constraints: list[ConstraintAnalysis]


class DependentClaimAnalysis(StrictModel):
    claim_id: str
    claim_number: int
    depends_on: list[int]
    added_limitations: list[str]
    evidence: list[EvidenceRef]


class ClaimOntologyExtraction(StrictModel):
    independent_claims: list[IndependentClaimAnalysis]
    dependent_claims: list[DependentClaimAnalysis]


class ProblemAnalysis(StrictModel):
    problem_assertion_id: str
    problem_id: str | None
    canonical_problem: str | None
    korean_name: str | None
    role: str
    target_expressions: list[str]
    cause_expressions: list[str]
    problem_status: str
    normalization_status: str
    evidence: EvidenceRef


class EffectAnalysis(StrictModel):
    effect_assertion_id: str
    effect_id: str | None
    canonical_effect: str | None
    korean_name: str | None
    role: str
    design_attribute_ids: list[str]
    effect_status: str
    normalization_status: str
    evidence: EvidenceRef


class ProblemEffectExtraction(StrictModel):
    problems: list[ProblemAnalysis]
    effects: list[EffectAnalysis]


class TechnologyAssignmentAnalysis(StrictModel):
    technology_id: str | None
    technology_name: str | None
    role: str
    rationale: str


class ArchitectureAssignmentAnalysis(StrictModel):
    architecture_id: str | None
    architecture_name: str | None
    role: str
    rationale: str


class TechnologyExtraction(StrictModel):
    technology_assignments: list[TechnologyAssignmentAnalysis]
    architecture_assignments: list[ArchitectureAssignmentAnalysis]


class ReportClaimElement(StrictModel):
    name: str
    original_expression: str
    explanation: str


class ReportIndependentClaim(StrictModel):
    claim_number: int
    plain_explanation: str
    claim_elements: list[ReportClaimElement]
    relation_explanation: str
    core_conditions: list[str]
    scope_note: str


class ThreeLineSummary(StrictModel):
    what_is_patent: str
    how_it_solves: str
    key_point: str


class Module1Report(StrictModel):
    three_line_summary: ThreeLineSummary
    core_problem: str
    independent_claims: list[ReportIndependentClaim]
    dependent_claims: str
    operation_principle_steps: list[str]
    technical_effects: str
    technology_classification: str
    core_technology_summary: str
    evidence_note: str


class CandidateOntologyFingerprint(StrictModel):
    publication_number: str
    technology_ids: list[str]
    architecture_ids: list[str]
    problem_ids: list[str]
    function_ids: list[str]
    claim_element_ids: list[str]
    relation_ids: list[str]
    solution_summary: str
    claim_focus: str


class CandidateBatchExtraction(StrictModel):
    candidates: list[CandidateOntologyFingerprint]


class RelatedPatentNarrative(StrictModel):
    publication_number: str
    selection_reason: str
    shared_problem: str
    common_points: list[str]
    differences: list[str]
    technical_development: str


class Module2Report(StrictModel):
    overview: str
    selection_method: str
    related_patents: list[RelatedPatentNarrative]
    comparison_summary: str
