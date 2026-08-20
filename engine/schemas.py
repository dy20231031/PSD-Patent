from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


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
