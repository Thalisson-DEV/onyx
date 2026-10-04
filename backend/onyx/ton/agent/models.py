"""Bounded inputs for the TON chat tools."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from onyx.ton.sources.models import SourceView


class ToolQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: UUID | None = None
    finding_id: UUID | None = None
    occurrence_id: UUID | None = None
    review_run_id: UUID | None = None
    normalization_run_id: UUID | None = None
    structure_version_id: UUID | None = None
    run_id: UUID | None = None
    request_id: UUID | None = None
    period: date | None = None
    unit_id: UUID | None = None
    blocking: bool | None = None
    blocker: str | None = Field(default=None, min_length=1, max_length=100)
    # Unit name or NG code as the user wrote it; resolved against visible units.
    unit: str | None = Field(default=None, min_length=1, max_length=100)
    limit: int = Field(default=10, ge=1, le=25)
    offset: int = Field(default=0, ge=0, le=10000)


class StoredDreContext(BaseModel):
    run_id: UUID
    period: date
    unit_id: UUID | None
    structure_version_id: UUID
    status: str


class FinancialBaseContext(BaseModel):
    normalization_run_id: UUID
    source_id: UUID
    review_run_id: UUID
    periods: list[date]
    source_name: str
    stored_dre_results: list[StoredDreContext]


class UnitContext(BaseModel):
    unit_id: UUID
    code: str
    name: str


class FinancialContext(BaseModel):
    bases: list[FinancialBaseContext]
    structure_version_ids: list[UUID]
    units: list[UnitContext] = []


class OverviewLine(BaseModel):
    linha: str
    realizado: str
    acumulado_no_ano: str
    orcado: str | None = None


class OverviewFinding(BaseModel):
    titulo: str
    impede_dre: bool
    situacao: str
    registros: int


class OverviewBlocker(BaseModel):
    bloqueio: str
    quantidade: int
    onde_resolver: str


class ClosingOverview(BaseModel):
    """Everything a period/unit closing question needs, in one tool call.

    Values are the persisted DRE lines, the same ones the DRE screen shows.
    """

    periodo: date
    ultimo_periodo_disponivel: date | None
    periodos_disponiveis: list[date]
    escopo: str
    unidade_solicitada_nao_encontrada: str | None = None
    unidades_candidatas: list[str] = []
    fonte: str | None
    situacao_dre: str
    bloqueios: list[OverviewBlocker]
    dre_calculada: bool
    linhas_dre: list[OverviewLine]
    achados_abertos_na_revisao: int
    achados_que_impedem_dre: int
    principais_achados: list[OverviewFinding]
    registros_na_base: int | None
    registros_excluidos: int | None
    onde_conferir: dict[str, str]
    limitacoes: list[str]
    # For follow-up tools (evidence, result); never shown to the user.
    normalization_run_id: UUID | None = None
    structure_version_id: UUID | None = None
    unit_id: UUID | None = None
    run_id: UUID | None = None


class ImportExecutionSummary(BaseModel):
    execution_id: UUID
    snapshot_id: UUID
    status: str
    finished_at: datetime | None
    imported_records: int | None
    rejected_records: int | None
    warnings: int | None
    errors: int | None


class SourceToolStatus(BaseModel):
    source: SourceView
    last_successful_import_at: datetime | None
    executions: list[ImportExecutionSummary]
    review_run_ids: list[UUID]


class OccurrenceSummary(BaseModel):
    occurrence_id: UUID
    reference: str
    title: str
    status: str
    criticality: str
    open_cycles: int
    last_detected_at: datetime
    owner: str | None
    deadline: date | None
    assignment_status: str | None
    overdue: bool
    requires_human_closure: bool
    verification_criterion: str | None


class OccurrencePage(BaseModel):
    as_of: date
    items: list[OccurrenceSummary]
    has_more: bool
    next_offset: int | None
    scope: str = "Ocorrências autorizadas; página não representa o total."
    recommendation: str = (
        "Confirmar ação, responsável e prazo. Nenhuma ocorrência foi encerrada."
    )
