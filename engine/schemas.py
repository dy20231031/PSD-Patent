from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class RawPatentSource(BaseModel):
    input_type: str
    filename: str | None = None
    page_count: int | None = None
    text_char_count: int = 0
    average_chars_per_page: float | None = None
    extraction_method: str
    ocr_used: bool = False
    warnings: list[str] = Field(default_factory=list)


class RawPatentMetadata(BaseModel):
    publication_number: str | None = None
    publication_number_raw: str | None = None
    title: str | None = None
    applicant: str | None = None
    filename: str | None = None
    pdf_metadata: dict[str, str] = Field(default_factory=dict)


class RawClaim(BaseModel):
    claim_id: str
    claim_number: int
    claim_type: str
    depends_on: list[int] = Field(default_factory=list)
    text: str


class RawPatent(BaseModel):
    schema_version: str = "raw-patent-v0.1"
    source: RawPatentSource
    metadata: RawPatentMetadata
    abstract: str = ""
    background: str = ""
    summary: str = ""
    figure_description: str = ""
    description: str = ""
    claims: list[RawClaim] = Field(default_factory=list)
    parser_diagnostics: dict[str, Any] = Field(default_factory=dict)
    raw_text: str = ""


class Evidence(BaseModel):
    evidence_id: str
    source_scope: str
    source_section: str | None = None
    claim_id: str | None = None
    evidence_text: str
    evidence_level: str
    normalization_status: str | None = None


class ClaimElementInstance(BaseModel):
    element_instance_id: str
    claim_id: str
    master_element_id: str | None = None
    original_expression: str
    instance_index: int | None = None
    role: str | None = None
    position: str | None = None
    normalization_status: str = "unmapped_candidate"
    attributes: dict[str, Any] = Field(default_factory=dict)
    evidence_id: str | None = None


class RelationAssertion(BaseModel):
    relation_assertion_id: str
    subject: str
    predicate: str
    object: str | None = None
    object_set: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    evidence_id: str | None = None


class StructuredPatent(BaseModel):
    patent: dict[str, Any]
    technology_assignments: list[dict[str, Any]] = Field(default_factory=list)
    architecture_assignments: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[dict[str, Any]] = Field(default_factory=list)
    problem_assertions: list[dict[str, Any]] = Field(default_factory=list)
    effect_assertions: list[dict[str, Any]] = Field(default_factory=list)
    problem_effect_links: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
