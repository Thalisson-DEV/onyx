"""TON domain queries in the existing Onyx tool runtime."""

import json
from typing import Any, ClassVar

from pydantic import ValidationError

from onyx.chat.emitter import Emitter
from onyx.db.engine.sql_engine import get_session_with_tenant
from onyx.db.models import User
from onyx.error_handling.exceptions import OnyxError
from onyx.server.query_and_chat.placement import Placement
from onyx.server.query_and_chat.streaming_models import (
    CustomToolDelta,
    CustomToolStart,
    Packet,
)
from onyx.ton.agent.models import ToolQuery
from onyx.ton.agent.service import query_domain
from onyx.tools.interface import Tool
from onyx.tools.models import CustomToolCallSummary, ToolCallException, ToolResponse
from shared_configs.contextvars import get_current_tenant_id


class TonDomainTool(Tool[None]):
    NAME: ClassVar[str]
    DESCRIPTION: ClassVar[str]
    FIELDS: ClassVar[tuple[str, ...]] = ()
    REQUIRED: ClassVar[tuple[str, ...]] = ()

    def __init__(self, tool_id: int, emitter: Emitter, user: User) -> None:
        super().__init__(emitter)
        self._id = tool_id
        self._user_id = user.id
        self._tenant_id = get_current_tenant_id()

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self.NAME

    @property
    def description(self) -> str:
        return self.DESCRIPTION

    @property
    def display_name(self) -> str:
        return self.DESCRIPTION

    def tool_definition(self) -> dict[str, Any]:
        properties = ToolQuery.model_json_schema()["properties"]
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {key: properties[key] for key in self.FIELDS},
                    "required": list(self.REQUIRED),
                    "additionalProperties": False,
                },
            },
        }

    def emit_start(self, placement: Placement) -> None:
        self.emitter.emit(
            Packet(
                placement=placement,
                obj=CustomToolStart(tool_name=self.name, tool_id=self.id),
            )
        )

    def run(
        self, placement: Placement, override_kwargs: None, **llm_kwargs: Any
    ) -> ToolResponse:
        del override_kwargs
        try:
            if set(llm_kwargs) - set(self.FIELDS):
                raise ValueError("Parâmetro não permitido")
            query = ToolQuery.model_validate(llm_kwargs)
            with get_session_with_tenant(tenant_id=self._tenant_id) as session:
                user = session.get(User, self._user_id)
                if user is None or not user.is_active:
                    raise ValueError("Usuário indisponível")
                result = query_domain(session, user, self.name, query)
                data = (
                    [item.model_dump(mode="json") for item in result]
                    if isinstance(result, list)
                    else result.model_dump(mode="json")
                )
        except (ValidationError, ValueError, OnyxError) as error:
            # Do not pass DB details or unauthorized identifiers to the model.
            raise ToolCallException(
                "TON query rejected",
                "Consulta indisponível. Verifique os parâmetros e sua autorização. Não invente dados.",
            ) from error
        response = json.dumps(data, ensure_ascii=False)
        if len(response) > 48000:
            raise ToolCallException(
                "TON response too large",
                "Reduza limit e consulte a próxima página com offset.",
            )
        self.emitter.emit(
            Packet(
                placement=placement,
                obj=CustomToolDelta(
                    tool_name=self.name,
                    tool_id=self.id,
                    response_type="json",
                    data=data,
                ),
            )
        )
        return ToolResponse(
            rich_response=CustomToolCallSummary(
                tool_name=self.name, response_type="json", tool_result=data
            ),
            llm_facing_response=response,
        )


class TonListSourcesTool(TonDomainTool):
    NAME = "ton_list_sources"
    DESCRIPTION = "Consultar fontes financeiras, última importação e diagnósticos. Importação manual não significa integração direta."


class TonGetSourceStatusTool(TonDomainTool):
    NAME = "ton_get_source_status"
    DESCRIPTION = "Consultar identidade e modo de aquisição de uma fonte autorizada."
    FIELDS = ("source_id", "limit")
    REQUIRED = ("source_id",)


class TonListFindingsTool(TonDomainTool):
    NAME = "ton_list_findings"
    DESCRIPTION = "Consultar pendências financeiras determinísticas com paginação. Não interpretar a página como total de achados."
    FIELDS = ("source_id", "review_run_id", "blocking", "limit", "offset")


class TonGetFindingTool(TonDomainTool):
    NAME = "ton_get_finding"
    DESCRIPTION = "Consultar pendência, recomendação e evidência com linhagem de planilha e linha."
    FIELDS = ("finding_id", "limit", "offset")
    REQUIRED = ("finding_id",)


class TonFinancialReviewSummaryTool(TonDomainTool):
    NAME = "ton_get_financial_review_summary"
    DESCRIPTION = "Consultar conjunto financeiro revisado, registros seguros e registros excluídos."
    FIELDS = REQUIRED = ("source_id", "review_run_id")


class TonDreReadinessTool(TonDomainTool):
    NAME = "ton_get_dre_readiness"
    DESCRIPTION = "Consultar bloqueios atuais da DRE por período e unidade. Não calcular nem aprovar."
    FIELDS = ("normalization_run_id", "structure_version_id", "period", "unit_id")
    REQUIRED = ("normalization_run_id", "structure_version_id", "period")


class TonDreResultTool(TonDomainTool):
    NAME = "ton_get_dre_result"
    DESCRIPTION = "Consultar resultado persistido da DRE. Retornar bloqueios quando pendente; nunca criar resultado financeiro."
    FIELDS = ("run_id", "limit", "offset")
    REQUIRED = ("run_id",)


class TonFinancialContextTool(TonDomainTool):
    NAME = "ton_get_financial_context"
    DESCRIPTION = "Descobrir identificadores autorizados de bases normalizadas e versões de estrutura DRE. Não inventar identificadores."
    FIELDS = ("limit", "offset")


TON_TOOL_CLASSES = (
    TonListSourcesTool,
    TonGetSourceStatusTool,
    TonListFindingsTool,
    TonGetFindingTool,
    TonFinancialReviewSummaryTool,
    TonDreReadinessTool,
    TonDreResultTool,
    TonFinancialContextTool,
)
