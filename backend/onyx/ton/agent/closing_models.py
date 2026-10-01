"""Inspectable closing outputs. Financial values stay in deterministic services."""

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClosingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    normalization_run_id: UUID | None = None
    structure_version_id: UUID | None = None
    period: date | None = None
    unit_id: UUID | None = None
    executive: bool = False


class SpecialistDefinition(BaseModel):
    key: str
    name: str
    objective: str
    domain: str
    required_capabilities: list[str]
    optional_capabilities: list[str] = []
    allowed_tools: list[str]
    output_contract: str = "Situação, evidência, impacto, recomendação e limitação."
    autonomy_policy: str = (
        "Consultar e recomendar. Decisões e aprovações exigem uma pessoa."
    )


class SpecialistOutcome(BaseModel):
    key: str
    name: str = ""
    status: Literal["Operacional", "Parcial", "Bloqueado"]
    reason: str
    facts: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)


class ClosingOutput(BaseModel):
    period: date
    scope: str
    normalization_run_id: UUID | None = None
    structure_version_id: UUID | None = None
    unit_id: UUID | None = None
    data_context: str
    sources: list[dict[str, Any]]
    specialists: list[SpecialistOutcome]
    findings: list[dict[str, Any]]
    findings_scope: str
    findings_page_limit: int = 10
    findings_may_have_more: bool
    dre_status: str
    blockers: dict[str, int]
    executive_brief: dict[str, str]
    generated_at: datetime


class PublishedClosing(BaseModel):
    run_id: UUID
    report_id: UUID
    revision_id: UUID
    status: str
    report_url: str
    download_url: str
    output: ClosingOutput
    steps: list[dict[str, str | None]]
    routine_code: str | None = None


class PublicationLink(BaseModel):
    run_id: UUID
    revision_id: UUID
    status: str
    period: date
    data_context: str
    executive_brief: dict[str, str]
    report_url: str
    download_url: str
