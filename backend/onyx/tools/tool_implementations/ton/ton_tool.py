"""TON domain queries in the existing Onyx tool runtime."""

import datetime
import json
from decimal import Decimal
from typing import Any, ClassVar
from uuid import UUID

from pydantic import BaseModel, ValidationError

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
from onyx.ton.agent.action_models import (
    ActionKind,
    AdjustmentPayload,
    AutomationRunPayload,
    AutomationStatusPayload,
    ClassificationConfirmPayload,
    ClassificationPayload,
    ControllerRulePayload,
    LedgerRegisterPayload,
    OccurrenceAssignPayload,
    R1SchedulePayload,
    RecalculatePayload,
    ReviewDecisionPayload,
    SourceImportPayload,
    StructureChangePayload,
    StructureCreatePayload,
    TreatmentPayload,
    UnitAssignmentPayload,
)
from onyx.ton.agent.labels import humanize
from onyx.ton.agent.models import ToolQuery
from onyx.ton.agent.policy import SYNTHETIC_DATA_NOTICE, uses_synthetic_demo_data
from onyx.ton.agent.service import query_domain
from onyx.ton.automations import drafter as automation_drafter
from onyx.tools.interface import Tool
from onyx.tools.models import CustomToolCallSummary, ToolCallException, ToolResponse
from shared_configs.contextvars import get_current_tenant_id

TON_TOOL_DISPLAY_NAMES = {
    "ton_list_sources": "Fontes financeiras",
    "ton_get_source_status": "Estado da fonte",
    "ton_list_findings": "Pendências financeiras",
    "ton_list_payables": "Agenda de pagamentos",
    "ton_get_finding": "Evidência da pendência",
    "ton_get_financial_review_summary": "Resumo da revisão financeira",
    "ton_get_dre_readiness": "Prontidão da DRE",
    "ton_get_dre_result": "Resultado da DRE",
    "ton_get_financial_context": "Contexto financeiro",
    "ton_get_closing_overview": "Fechamento do período",
    "ton_analyze_closing": "Análise do fechamento",
    "ton_generate_closing_report": "Relatório de fechamento",
    "ton_generate_executive_brief": "Resumo executivo",
    "ton_get_billing_summary": "Resumo do faturamento",
    "ton_get_budget_summary": "Resumo do orçamento",
    "ton_get_reconciliation_summary": "Resumo da conciliação",
    "ton_list_occurrences": "Ocorrências",
    "ton_get_occurrence": "Detalhe da ocorrência",
    "ton_list_overdue_actions": "Ações vencidas",
    "ton_get_readiness_evidence": "Evidência da prontidão",
    "ton_get_recent_changes": "Mudanças após decisões",
    "ton_draft_automation": "Rascunho de automação",
    "ton_get_dre_structure": "Estrutura da DRE",
    "ton_propose_dre_structure_change": "Proposta na estrutura da DRE",
    "ton_propose_dre_create": "Proposta de DRE nova",
    "ton_propose_dre_adjustment": "Proposta de ajuste da DRE",
    "ton_propose_closing_treatment": "Proposta de tratamento",
    "ton_propose_dre_recalculation": "Proposta de recálculo",
    "ton_propose_source_import": "Proposta de importação",
    "ton_search_entries": "Busca de lançamentos",
    "ton_supplier_summary": "Fornecedores",
    "ton_run_financial_test": "Teste financeiro",
    "ton_compare_dre": "Comparação da DRE",
    "ton_get_dre_line_entries": "Lançamentos da linha",
    "ton_propose_account_classification": "Proposta de classificação",
    "ton_propose_classification_confirm": "Proposta de confirmação",
    "ton_propose_review_decision": "Proposta de decisão",
    "ton_propose_unit_assignment": "Proposta de unidade",
    "ton_propose_automation_status": "Proposta na automação",
    "ton_propose_automation_run": "Proposta de execução",
    "ton_list_classification_queue": "Contas para classificar",
    "ton_list_unit_missing": "Lançamentos sem unidade",
    "ton_list_automations": "Automações",
    "ton_propose_controller_rule": "Proposta de regra",
    "ton_get_controller_rules": "Regras da Controladoria",
    "ton_propose_ledger_registration": "Proposta de registro no ledger",
    "ton_propose_occurrence_assignment": "Proposta de responsável",
    "ton_propose_daily_sweep": "Proposta de varredura diária",
    "ton_get_daily_sweep": "Varredura diária",
}


class TonDomainTool(Tool[None]):
    NAME: ClassVar[str]
    DESCRIPTION: ClassVar[str]
    FIELDS: ClassVar[tuple[str, ...]] = ()
    REQUIRED: ClassVar[tuple[str, ...]] = ()

    def __init__(
        self,
        tool_id: int,
        emitter: Emitter,
        user: User,
        chat_session_id: UUID | None = None,
        chat_file_ids: list[UUID] | None = None,
    ) -> None:
        super().__init__(emitter)
        self._id = tool_id
        self._user_id = user.id
        self._tenant_id = get_current_tenant_id()
        self._chat_session_id = chat_session_id
        self._chat_file_ids = list(chat_file_ids or [])

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
        return TON_TOOL_DISPLAY_NAMES[self.name]

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
                obj=CustomToolStart(tool_name=self.display_name, tool_id=self.id),
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
            # Business messages only: database errors are not caught here, so
            # no DB detail reaches the model.
            if isinstance(error, ValidationError):
                first = error.errors()[0]
                reason = f"parâmetro {'.'.join(str(item) for item in first['loc'])}: {first['msg']}"
            elif isinstance(error, OnyxError):
                reason = error.detail
            else:
                reason = str(error)
            raise ToolCallException(
                "TON query rejected",
                f"Consulta não feita ({reason[:300]}). Corrija os parâmetros sem repetir a mesma chamada, "
                "ou explique a limitação. Não invente dados.",
            ) from error
        if uses_synthetic_demo_data():
            data = {"data_context": SYNTHETIC_DATA_NOTICE, "data": data}
        data = humanize(data)
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
                    tool_name=self.display_name,
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
    DESCRIPTION = "Descobrir identificadores autorizados de bases normalizadas, versões de estrutura DRE, unidades e DREs calculadas. Filtre por period e unit_id para ver os cálculos daquele escopo. Não inventar identificadores."
    FIELDS = ("period", "unit_id", "limit", "offset")


class TonClosingOverviewTool(TonDomainTool):
    NAME = "ton_get_closing_overview"
    DESCRIPTION = "Fechamento de um mês e unidade em uma chamada: base mais recente, situação da DRE, bloqueios e onde resolvê-los, valores da DRE calculada (os mesmos da tela DRE) e achados abertos da revisão. period é o primeiro dia do mês (sem ele, o último mês disponível); unit é o nome ou código da unidade como o usuário escreveu (sem ela, o consolidado)."
    FIELDS = ("period", "unit")


class TonAnalyzeClosingTool(TonDomainTool):
    NAME = "ton_analyze_closing"
    DESCRIPTION = "Analisar fechamento com CFO, AUDITOR e CEO usando serviços determinísticos. Sem parâmetros, selecionar a base mais recente e informar seu período. Não aprovar nem calcular DRE."
    FIELDS = ("normalization_run_id", "structure_version_id", "period", "unit_id")


class TonClosingReportTool(TonDomainTool):
    NAME = "ton_generate_closing_report"
    DESCRIPTION = "Gerar relatório imutável de pendências do fechamento, com evidências e link para abrir e baixar. Exige permissão de gestão de relatórios. Pode repetir request_id para recuperar a mesma publicação."
    FIELDS = (
        "request_id",
        "normalization_run_id",
        "structure_version_id",
        "period",
        "unit_id",
    )


class TonExecutiveBriefTool(TonClosingReportTool):
    NAME = "ton_generate_executive_brief"
    DESCRIPTION = "Gerar resumo executivo persistido dos resultados CFO e AUDITOR, sem estimar valores. Retornar link da publicação."


class TonBillingSummaryTool(TonDomainTool):
    NAME = "ton_get_billing_summary"
    DESCRIPTION = "Consultar quantidade de registros normalizados de faturamento no período, alinhamento do orçamento e conciliação. Não equivale a total monetário nem aprovação."
    FIELDS = ("normalization_run_id", "period", "unit_id")
    REQUIRED = ("normalization_run_id", "period")


class TonBudgetSummaryTool(TonBillingSummaryTool):
    NAME = "ton_get_budget_summary"
    DESCRIPTION = "Consultar cobertura do orçamento no período e escopo, sem estimar valores ausentes."


class TonReconciliationSummaryTool(TonBillingSummaryTool):
    NAME = "ton_get_reconciliation_summary"
    DESCRIPTION = "Consultar conciliação determinística entre realizado e faturamento no período e escopo."


class TonListOccurrencesTool(TonDomainTool):
    NAME = "ton_list_occurrences"
    DESCRIPTION = "Consultar ocorrências autorizadas e a atribuição atual de responsável e prazo. Página não equivale ao total. Somente leitura."
    FIELDS = ("limit", "offset")


class TonGetOccurrenceTool(TonDomainTool):
    NAME = "ton_get_occurrence"
    DESCRIPTION = "Consultar uma ocorrência autorizada, seu estado, responsável, prazo e critério de verificação. Não encerrar nem alterar."
    FIELDS = REQUIRED = ("occurrence_id",)


class TonOverdueActionsTool(TonListOccurrencesTool):
    NAME = "ton_list_overdue_actions"
    DESCRIPTION = "Consultar somente atribuições atuais abertas com prazo anterior à data UTC, em ocorrências não encerradas. Prazo ausente não significa vencido. Nenhuma ação é encerrada."


class TonReadinessEvidenceTool(TonDomainTool):
    NAME = "ton_get_readiness_evidence"
    DESCRIPTION = "Detalhar um bloqueio da Prontidão financeira usando seu rótulo retornado pela análise. Paginação e evidências de fonte da base inteira, não apenas do mês. Lacunas de cobertura retornam orientação, sem inventar linhas."
    FIELDS = (
        "normalization_run_id",
        "structure_version_id",
        "blocker",
        "unit_id",
        "limit",
        "offset",
    )
    REQUIRED = ("normalization_run_id", "structure_version_id", "blocker")


class TonRecentChangesTool(TonDomainTool):
    NAME = "ton_get_recent_changes"
    DESCRIPTION = "Consultar o que mudou na prontidão da DRE desde a base anterior e as decisões humanas registradas (quem, quando, justificativa, versão e se já foram aplicadas). Sem parâmetros, usa a base mais recente. Não aprovar nem recalcular."
    FIELDS = ("normalization_run_id", "structure_version_id", "unit_id", "limit")


class TonDraftAutomationTool(TonDomainTool):
    """Turns a chat request into an automation draft. Writes only a draft
    (a TON suggestion); nothing runs until a person activates it."""

    NAME = "ton_draft_automation"
    DESCRIPTION = (
        "Criar ou ajustar um RASCUNHO de automação (workflow) quando a pessoa pedir algo como "
        "'quando acontecer X, faça Y', 'toda segunda envie...', 'avise quando...', 'leia este "
        "documento e...'. Passe o pedido completo em 'request', em português, com gatilho, condições, "
        "ações, destinatários e o texto desejado. Para ajustar um rascunho já criado nesta conversa, passe "
        "também 'automation_id'. O rascunho não roda: a pessoa revisa e ativa no editor. Depois de chamar, "
        "resuma os passos e o que falta (ex.: e-mail de destinatário), sem inventar endereços."
    )

    def tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "request": {
                            "type": "string",
                            "description": "O pedido da pessoa, completo, em português.",
                        },
                        "automation_id": {
                            "type": "string",
                            "description": "Id da automação a ajustar (opcional).",
                        },
                    },
                    "required": ["request"],
                    "additionalProperties": False,
                },
            },
        }

    def run(
        self, placement: Placement, override_kwargs: None, **llm_kwargs: Any
    ) -> ToolResponse:
        del override_kwargs
        request = str(llm_kwargs.get("request") or "").strip()
        raw_id = llm_kwargs.get("automation_id")
        try:
            if set(llm_kwargs) - {"request", "automation_id"} or len(request) < 5:
                raise ValueError("Pedido inválido")
            automation_id = UUID(str(raw_id)) if raw_id else None
            with get_session_with_tenant(tenant_id=self._tenant_id) as session:
                user = session.get(User, self._user_id)
                if user is None or not user.is_active:
                    raise ValueError("Usuário indisponível")
                result = automation_drafter.draft_automation(session, user, request[:4000], automation_id)
                dumped = result.model_dump(mode="json", exclude={"definition"})
                # "kind" tells the chat which card to draw; the automation's own
                # kind (E-mail, Alerta…) travels as automation_kind.
                data = {**dumped, "kind": "automation_draft", "automation_kind": dumped["kind"]}
        except OnyxError as error:
            raise ToolCallException(
                "TON automation draft rejected",
                f"Não foi possível criar o rascunho: {error.detail}. Explique à pessoa e peça o que faltar.",
            ) from error
        except (ValidationError, ValueError) as error:
            raise ToolCallException(
                "TON automation draft rejected",
                "Pedido inválido para rascunho de automação. Peça à pessoa o gatilho, as ações e os destinatários.",
            ) from error
        self.emitter.emit(
            Packet(
                placement=placement,
                obj=CustomToolDelta(
                    tool_name=self.display_name,
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
            llm_facing_response=json.dumps(data, ensure_ascii=False),
        )


def _inline_schema(model: type[BaseModel]) -> dict[str, Any]:
    """JSON schema of ``model`` with every $ref resolved and titles dropped."""
    schema = model.model_json_schema()
    definitions = schema.pop("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                return resolve(definitions[node["$ref"].split("/")[-1]])
            return {
                key: resolve(value) for key, value in node.items() if key != "title"
            }
        if isinstance(node, list):
            return [resolve(item) for item in node]
        return node

    return resolve(schema)


class TonProposeActionTool(TonDomainTool):
    """Validates a change and shows it as a card with Aplicar and Cancelar.
    Nothing changes until the person clicks Aplicar."""

    KIND: ClassVar[ActionKind]
    PAYLOAD: ClassVar[type[BaseModel]]

    def tool_definition(self) -> dict[str, Any]:
        parameters = _inline_schema(self.PAYLOAD)
        parameters["additionalProperties"] = False
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
            },
        }

    def run(
        self, placement: Placement, override_kwargs: None, **llm_kwargs: Any
    ) -> ToolResponse:
        del override_kwargs
        from onyx.db.ton import agent_actions

        try:
            with get_session_with_tenant(tenant_id=self._tenant_id) as session:
                user = session.get(User, self._user_id)
                if user is None or not user.is_active:
                    raise ValueError("Usuário indisponível")
                view = agent_actions.propose(
                    session, user, self.KIND, llm_kwargs, self._chat_session_id
                )
        except (ValueError, OnyxError) as error:
            message = error.detail if isinstance(error, OnyxError) else str(error)
            raise ToolCallException(
                "TON action proposal rejected",
                f"A proposta não foi criada: {message}. Corrija o pedido ou pergunte à pessoa o que falta.",
            ) from error
        data = {**view.model_dump(mode="json"), "kind": "agent_action", "action_kind": view.kind.value}
        self.emitter.emit(
            Packet(
                placement=placement,
                obj=CustomToolDelta(
                    tool_name=self.display_name,
                    tool_id=self.id,
                    response_type="json",
                    data=data,
                ),
            )
        )
        llm_data = {
            "proposta": view.title,
            "situacao": "AGUARDANDO A PESSOA CLICAR EM APLICAR",
            "resumo": view.preview.resumo,
            "escopo": view.preview.escopo,
            "linhas_antes_depois": [
                item.model_dump(mode="json") for item in view.preview.linhas
            ],
            "avisos": view.preview.avisos,
            "instrucao": (
                "Há um ATENÇÃO nos avisos: a proposta tem um erro de fórmula. Faça agora uma nova proposta "
                "corrigida (ela substitui esta) antes de responder à pessoa."
                if any(item.startswith(agent_actions.LOOSE_MARK) for item in view.preview.avisos)
                else "O cartão com Aplicar e Cancelar já está na tela. Diga em poucas frases o que muda e peça "
                "para conferir e clicar em Aplicar. Nunca diga que já aplicou."
            ),
        }
        return ToolResponse(
            rich_response=CustomToolCallSummary(
                tool_name=self.name, response_type="json", tool_result=data
            ),
            llm_facing_response=json.dumps(llm_data, ensure_ascii=False),
        )


class TonProposeStructureChangeTool(TonProposeActionTool):
    NAME = "ton_propose_dre_structure_change"
    KIND = ActionKind.DRE_STRUCTURE_CHANGE
    PAYLOAD = StructureChangePayload
    DESCRIPTION = (
        "Propor mudança na estrutura de uma DRE (gerencial, caixa, economica ou outra, em structure_id): criar "
        "linha ou grupo, renomear, mover, ocultar, tirar do resultado, mudar a origem da linha, mudar fórmula de "
        "total, remover linha vazia ou mover natureza do NG para outra linha (só na gerencial). Antes, leia os "
        "códigos com ton_get_dre_structure da mesma DRE. Origens de linha: NG_ACCOUNTS (naturezas do NG), BILLING "
        "(notas da planilha de faturamento: billing_fields como service_amount para o bruto, iss_retained, "
        "iss_invoice, total_retained; billing_percent para um percentual do valor, ex.: taxa de administração 2% "
        "= service_amount com billing_percent=2; negate=true para impostos, taxas e retenções) e ADJUSTMENT "
        "(valores informados pela Controladoria, ajustados depois com ton_propose_dre_adjustment). Linhas e grupos "
        "novos recebem códigos em sequência a partir de proximo_codigo_novo da leitura (a1, a2… na gerencial; "
        "x1, x2… nas outras DREs), pulando os que já existem; use esses códigos em after_code, code e operands "
        "das operações seguintes. A proposta mostra a DRE antes e depois; só muda quando a pessoa clica em Aplicar."
    )


class TonProposeStructureCreateTool(TonProposeActionTool):
    NAME = "ton_propose_dre_create"
    KIND = ActionKind.DRE_STRUCTURE_CREATE
    PAYLOAD = StructureCreatePayload
    DESCRIPTION = (
        "Propor uma DRE nova da Controladoria (ex.: \"DRE - BI Caixa\") começando como cópia da DRE Caixa ou da "
        "Econômica, acompanhando a gerencial como elas. Use quando a pessoa pedir um modelo novo de DRE ou "
        "fechamento que não existe; se ela quer mudar uma DRE existente, use ton_propose_dre_structure_change. "
        "Depois de aplicada, leia a DRE nova com ton_get_dre_structure e proponha as mudanças dela (grupos, "
        "faturamento bruto, impostos, percentuais) numa única proposta. Só muda quando a pessoa clica em Aplicar."
    )


class TonProposeAdjustmentTool(TonProposeActionTool):
    NAME = "ton_propose_dre_adjustment"
    KIND = ActionKind.DRE_ADJUSTMENT
    PAYLOAD = AdjustmentPayload
    DESCRIPTION = (
        "Propor valores da Controladoria para uma linha de origem ADJUSTMENT (ex.: PIS/COFINS do mês enquanto "
        "a planilha não chega). Um valor por mês e unidade; sem unidade, entra só no consolidado. Valores "
        "positivos; a linha com negate=true deduz. Exige justificativa. Só muda quando a pessoa clica em Aplicar."
    )


class TonProposeTreatmentTool(TonProposeActionTool):
    NAME = "ton_propose_closing_treatment"
    KIND = ActionKind.CLOSING_TREATMENT
    PAYLOAD = TreatmentPayload
    DESCRIPTION = (
        "Propor tratamento de fechamento sobre uma natureza do NG: EXCLUDE (tirar da DRE), RECLASSIFY (mover "
        "para target_nature_code) ou REPLACE_BY_SOURCE. Mesmo treatment_key cria nova versão. Exige "
        "justificativa e evidência ditas pela pessoa; não invente. Ao aplicar, a base é atualizada e a DRE recalculada."
    )


class TonProposeRecalculationTool(TonProposeActionTool):
    NAME = "ton_propose_dre_recalculation"
    KIND = ActionKind.DRE_RECALCULATE
    PAYLOAD = RecalculatePayload
    DESCRIPTION = (
        "Propor o recálculo da DRE de janeiro até o mês, no consolidado e nas unidades pedidas "
        "(units=['todas'] para todas). Use depois de mudanças aplicadas em unidades ou quando a DRE não está calculada."
    )


class TonProposeImportTool(TonProposeActionTool):
    NAME = "ton_propose_source_import"
    KIND = ActionKind.SOURCE_IMPORT
    PAYLOAD = SourceImportPayload
    DESCRIPTION = (
        "Propor a importação de um arquivo anexado nesta conversa como nova versão de uma fonte: "
        "financial_launches (lançamentos do NG), billing_invoices (faturamento/notas fiscais), budget "
        "(dotação/orçamento) ou installments (parcelamentos pagos). Use o id do arquivo anexado. A prévia diz "
        "quantas linhas entram, quais decisões continuam e quais voltam para decisão. Ao aplicar, importa, "
        "atualiza a base e recalcula a DRE."
    )

    def run(
        self, placement: Placement, override_kwargs: None, **llm_kwargs: Any
    ) -> ToolResponse:
        from onyx.db.ton import agent_actions

        with get_session_with_tenant(tenant_id=self._tenant_id) as session:
            user = session.get(User, self._user_id)
            files = (
                agent_actions.attached_spreadsheets(session, user, self._chat_file_ids)
                if user is not None
                else []
            )
        wanted_id = str(llm_kwargs.get("file_id") or "")
        wanted_name = str(llm_kwargs.get("file_name") or "").strip().lower()
        matches = [
            (file_id, name)
            for file_id, name in files
            if (wanted_id and str(file_id) == wanted_id)
            or (wanted_name and wanted_name in name.lower())
        ]
        if not wanted_id and not wanted_name:
            matches = files
        if len(matches) != 1:
            names = ", ".join(name for _, name in files) or "nenhuma"
            raise ToolCallException(
                "TON import file not resolved",
                f"Não identifiquei um único arquivo. Planilhas anexadas nesta conversa: {names}. "
                "Passe file_name com o nome exato ou peça para anexar o arquivo.",
            )
        llm_kwargs = {
            **{key: value for key, value in llm_kwargs.items() if key != "file_name"},
            "file_id": str(matches[0][0]),
        }
        return super().run(placement, override_kwargs, **llm_kwargs)


class TonDreStructureTool(TonDomainTool):
    NAME = "ton_get_dre_structure"
    DESCRIPTION = (
        "Ler a estrutura de uma DRE como está: código, nome, grupo, origem de cada linha, naturezas ligadas, "
        "fórmulas dos totais, campos de faturamento, o que pode ser editado nela e o próximo código de linha nova. "
        "Também lista todas as DREs existentes (gerencial, caixa, econômica e as criadas pela Controladoria). "
        "Use antes de propor mudanças na estrutura ou ajustes."
    )

    def tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "structure_id": {
                            "type": "string",
                            "description": "Qual DRE: gerencial, caixa, economica, o nome de outra DRE ou o structure_id. Vazio: a gerencial.",
                        }
                    },
                    "required": [],
                    "additionalProperties": False,
                },
            },
        }

    def run(
        self, placement: Placement, override_kwargs: None, **llm_kwargs: Any
    ) -> ToolResponse:
        del override_kwargs
        from onyx.db.ton import agent_actions

        try:
            raw = llm_kwargs.get("structure_id")
            with get_session_with_tenant(tenant_id=self._tenant_id) as session:
                user = session.get(User, self._user_id)
                if user is None or not user.is_active:
                    raise ValueError("Usuário indisponível")
                data = agent_actions.structure_for_chat(
                    session, user, str(raw) if raw else None
                )
        except (ValueError, OnyxError) as error:
            message = error.detail if isinstance(error, OnyxError) else str(error)
            raise ToolCallException(
                "TON structure read rejected",
                f"Estrutura não lida: {message}. Corrija o nome da DRE (gerencial, caixa, economica ou o nome "
                "exato) e não repita o mesmo pedido. Não invente códigos de linha.",
            ) from error
        self.emitter.emit(
            Packet(
                placement=placement,
                obj=CustomToolDelta(
                    tool_name=self.display_name,
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
            llm_facing_response=json.dumps(data, ensure_ascii=False),
        )


def _date(value: Any) -> datetime.date | None:
    if not value:
        return None
    text = str(value)
    if len(text) == 7:
        text = f"{text}-01"
    return datetime.date.fromisoformat(text[:10]).replace(day=1)


def _decimal(value: Any, default: str) -> Decimal:
    return Decimal(str(value)) if value not in (None, "") else Decimal(default)


PERIOD = {"type": "string", "description": "Mês no formato AAAA-MM. Vazio: último mês da base."}
UNIT = {"type": "string", "description": "Nome ou código da unidade como a pessoa escreveu. Vazio: todas."}


class TonFunctionTool(TonDomainTool):
    """A read-only TON tool with its own parameters, answered by ``compute``."""

    PARAMETERS: ClassVar[dict[str, Any]] = {}

    def tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.PARAMETERS,
                    "required": [],
                    "additionalProperties": False,
                },
            },
        }

    def compute(self, session: Any, user: User, kwargs: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def run(
        self, placement: Placement, override_kwargs: None, **llm_kwargs: Any
    ) -> ToolResponse:
        del override_kwargs
        from onyx.db.ton.agent_investigations import InvestigationError, public

        try:
            if set(llm_kwargs) - set(self.PARAMETERS):
                raise InvestigationError("Parâmetro não permitido")
            with get_session_with_tenant(tenant_id=self._tenant_id) as session:
                user = session.get(User, self._user_id)
                if user is None or not user.is_active:
                    raise InvestigationError("Usuário indisponível")
                data = public(self.compute(session, user, llm_kwargs))
        except (InvestigationError, OnyxError, ValueError) as error:
            message = error.detail if isinstance(error, OnyxError) else str(error)
            raise ToolCallException(
                "TON investigation rejected",
                f"Consulta não feita: {message}. Corrija os parâmetros ou pergunte à pessoa.",
            ) from error
        response = json.dumps(data, ensure_ascii=False)
        if len(response) > 48000:
            raise ToolCallException(
                "TON response too large", "Resultado grande demais; filtre por unidade, natureza ou período."
            )
        self.emitter.emit(
            Packet(
                placement=placement,
                obj=CustomToolDelta(
                    tool_name=self.display_name,
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


class TonSearchEntriesTool(TonFunctionTool):
    NAME = "ton_search_entries"
    DESCRIPTION = (
        "Buscar lançamentos do NG por texto do histórico ou fornecedor, documento, natureza, unidade, período e "
        "faixa de valor. Devolve os maiores, a soma e a evidência (arquivo, planilha, linha). Use para perguntas "
        "como 'quanto pagamos à empresa X', 'ache o documento 392', 'locações de Mossoró em abril'."
    )
    PARAMETERS = {
        "text": {"type": "string", "description": "Palavras do histórico ou do fornecedor."},
        "document": {"type": "string", "description": "Número do documento."},
        "nature": {"type": "string", "description": "Código (ex.: 8.1.0001) ou nome da natureza."},
        "unit": UNIT,
        "period_from": PERIOD,
        "period_to": PERIOD,
        "min_amount": {"type": "number", "description": "Valor absoluto mínimo."},
        "max_amount": {"type": "number", "description": "Valor absoluto máximo."},
    }

    def compute(self, session: Any, user: User, kwargs: dict[str, Any]) -> dict[str, Any]:
        from onyx.db.ton import agent_investigations as inv

        return inv.search_entries(
            session,
            user,
            text=kwargs.get("text"),
            document=kwargs.get("document"),
            nature=kwargs.get("nature"),
            unit=kwargs.get("unit"),
            period_from=_date(kwargs.get("period_from")),
            period_to=_date(kwargs.get("period_to")),
            min_amount=_decimal(kwargs["min_amount"], "0") if "min_amount" in kwargs else None,
            max_amount=_decimal(kwargs["max_amount"], "0") if "max_amount" in kwargs else None,
        )


class TonSupplierSummaryTool(TonFunctionTool):
    NAME = "ton_supplier_summary"
    DESCRIPTION = (
        "Maiores fornecedores por valor no período, com número de lançamentos e unidades atendidas. Filtre por "
        "natureza e unidade. O fornecedor vem do histórico do NG ('PAGAMENTO A ...')."
    )
    PARAMETERS = {
        "nature": {"type": "string", "description": "Código ou nome da natureza."},
        "unit": UNIT,
        "period_from": PERIOD,
        "period_to": PERIOD,
    }

    def compute(self, session: Any, user: User, kwargs: dict[str, Any]) -> dict[str, Any]:
        from onyx.db.ton import agent_investigations as inv

        return inv.supplier_summary(
            session,
            user,
            nature=kwargs.get("nature"),
            unit=kwargs.get("unit"),
            period_from=_date(kwargs.get("period_from")),
            period_to=_date(kwargs.get("period_to")),
        )


class TonFinancialTestTool(TonFunctionTool):
    NAME = "ton_run_financial_test"
    DESCRIPTION = (
        "Rodar um teste financeiro do Prompt Mestre sobre a base real e devolver os candidatos com evidência: "
        "T1 grupo zerado, T2 desvio da média de 3 meses, T3 duplicidade, T4 receita NG × notas fiscais, "
        "T6 sinal invertido, T8 fornecedor × unidade, T9 competência retroativa, T10 evento não recorrente. "
        "Os limites são parâmetros do teste (diga quais usou); o resultado são candidatos para a pessoa conferir, "
        "nunca conclusão de erro ou fraude. Para uma varredura do mês, rode os testes mais úteis um a um."
    )
    PARAMETERS = {
        "test": {"type": "string", "enum": ["T1", "T2", "T3", "T4", "T6", "T8", "T9", "T10"]},
        "period": PERIOD,
        "period_from": PERIOD,
        "period_to": PERIOD,
        "unit": UNIT,
        "min_amount": {"type": "number", "description": "Valor mínimo em reais (padrão por teste)."},
        "min_percent": {"type": "number", "description": "T2: variação mínima em % (padrão 50)."},
        "factor": {"type": "number", "description": "T10: vezes a mediana (padrão 10)."},
        "min_units": {"type": "integer", "description": "T8: unidades no mesmo mês (padrão 5)."},
        "min_months": {"type": "integer", "description": "T9: meses de atraso (padrão 2)."},
    }

    def compute(self, session: Any, user: User, kwargs: dict[str, Any]) -> dict[str, Any]:
        from onyx.db.ton import agent_investigations as inv

        return inv.run_test(session, user, kwargs)


class TonCompareDreTool(TonFunctionTool):
    NAME = "ton_compare_dre"
    DESCRIPTION = (
        "Comparar a DRE calculada entre meses e/ou unidades lado a lado (valores da tela DRE). Ex.: Mossoró "
        "jan × set, ou todas as unidades em setembro. Use 'consolidado' para o total."
    )
    PARAMETERS = {
        "periods": {"type": "array", "items": PERIOD, "description": "Meses a comparar (até 12)."},
        "units": {"type": "array", "items": UNIT, "description": "Unidades (até 8); 'consolidado' para o total."},
    }

    def compute(self, session: Any, user: User, kwargs: dict[str, Any]) -> dict[str, Any]:
        from onyx.db.ton import agent_investigations as inv

        periods = [item for item in (_date(value) for value in kwargs.get("periods") or []) if item]
        return inv.compare_dre(session, user, periods, list(kwargs.get("units") or []))


class TonLineEntriesTool(TonFunctionTool):
    NAME = "ton_get_dre_line_entries"
    DESCRIPTION = (
        "Ver os lançamentos que compõem uma linha da DRE no mês e escopo (o mesmo detalhe do clique na linha da "
        "tela), com os maiores valores, tratamentos e evidência."
    )
    PARAMETERS = {
        "line": {"type": "string", "description": "Nome ou código da linha (ex.: Combustível, n3.01)."},
        "period": PERIOD,
        "unit": UNIT,
    }

    def compute(self, session: Any, user: User, kwargs: dict[str, Any]) -> dict[str, Any]:
        from onyx.db.ton import agent_investigations as inv

        return inv.line_entries(
            session, user, str(kwargs.get("line") or ""), _date(kwargs.get("period")), kwargs.get("unit")
        )


class TonProposeClassificationTool(TonProposeActionTool):
    NAME = "ton_propose_account_classification"
    KIND = ActionKind.ACCOUNT_CLASSIFICATION
    PAYLOAD = ClassificationPayload
    DESCRIPTION = (
        "Propor a natureza de contas do NG (classificação contábil) e, na mesma proposta, criar naturezas novas "
        "(new_naturezas: em um grupo existente, group, ou num grupo novo, new_group, dentro ou fora do resultado). "
        "Cada conta vai por código (8.1.0001) ou pelo nome exato da conta no NG; a natureza, por código, nome ou "
        "uma das novas. Pedidos no formato do BI da Controladoria — GRUPO › NATUREZA › detalhamento — são isto: "
        "o detalhamento são contas do NG (veja ton_list_classification_queue ou ton_search_entries); compare "
        "com a classificação atual e proponha só o que muda, numa proposta única: naturezas que faltam e contas "
        "que estão em outra natureza. Itens com código de rubrica de folha (ex.: 0001 - Salário Contratual) vêm "
        "do sistema de folha, não do NG: diga isso e não os invente; impostos, provisões e taxas calculadas são "
        "linhas de faturamento ou ajuste (ton_propose_dre_structure_change). Não crie linhas de ajuste zeradas "
        "para contas que existem no NG. A prévia avisa contas que entram ou saem do resultado. Ao aplicar, cria "
        "as naturezas, grava a classificação, atualiza a base e recalcula a DRE. Pode desfazer."
    )


class TonProposeClassificationConfirmTool(TonProposeActionTool):
    NAME = "ton_propose_classification_confirm"
    KIND = ActionKind.CLASSIFICATION_CONFIRM
    PAYLOAD = ClassificationConfirmPayload
    DESCRIPTION = "Propor confirmar, como estão, as naturezas sugeridas pelo assistente para as contas do NG listadas."


class TonProposeReviewDecisionTool(TonProposeActionTool):
    NAME = "ton_propose_review_decision"
    KIND = ActionKind.REVIEW_DECISION
    PAYLOAD = ReviewDecisionPayload
    DESCRIPTION = (
        "Propor a decisão de pendências da revisão do NG (ids de ton_list_occurrences ou ton_list_findings): "
        "ACKNOWLEDGE (ciente), REQUEST_SOURCE_CORRECTION (pedir correção na fonte), JUSTIFY_EXCEPTION (exceção "
        "justificada, com justification_category), MARK_FALSE_POSITIVE, CONFIRM_SOURCE_CORRECTION. O motivo vem "
        "da pessoa; não invente."
    )


class TonProposeUnitAssignmentTool(TonProposeActionTool):
    NAME = "ton_propose_unit_assignment"
    KIND = ActionKind.UNIT_ASSIGNMENT
    PAYLOAD = UnitAssignmentPayload
    DESCRIPTION = (
        "Propor a unidade de lançamentos do NG que vieram sem unidade (ids de ton_list_unit_missing). Pode "
        "sugerir a unidade pelo histórico, mas diga que é sugestão. Ao aplicar, atualiza a base e recalcula."
    )


class TonProposeAutomationStatusTool(TonProposeActionTool):
    NAME = "ton_propose_automation_status"
    KIND = ActionKind.AUTOMATION_STATUS
    PAYLOAD = AutomationStatusPayload
    DESCRIPTION = "Propor ativar (ACTIVE) ou pausar (PAUSED) uma automação pelo nome."


class TonProposeAutomationRunTool(TonProposeActionTool):
    NAME = "ton_propose_automation_run"
    KIND = ActionKind.AUTOMATION_RUN
    PAYLOAD = AutomationRunPayload
    DESCRIPTION = (
        "Propor executar uma automação agora pelo nome. test=true (padrão) manda e-mails só para a pessoa; "
        "test=false executa de verdade."
    )


class TonProposeControllerRuleTool(TonProposeActionTool):
    NAME = "ton_propose_controller_rule"
    KIND = ActionKind.CONTROLLER_RULE
    PAYLOAD = ControllerRulePayload
    DESCRIPTION = (
        "Propor lembrar uma regra que a pessoa disse sobre como a Controladoria trabalha (ex.: parcelamento "
        "fica fora do resultado; receita é sempre pelo bruto; mútuo nunca entra na DRE). Para trocar ou "
        "esquecer uma regra, passe rule_key (e archive=true para esquecer). Use quando a pessoa disser "
        "sempre, nunca, a regra é, lembre que."
    )


class TonControllerRulesTool(TonFunctionTool):
    NAME = "ton_get_controller_rules"
    DESCRIPTION = (
        "Ler as regras da Controladoria lembradas pelo TON (decisões permanentes de como tratar receita, "
        "parcelamentos, mútuos, classificação). Leia antes de propor mudanças ou quando a pessoa perguntar "
        "como algo deve ser tratado."
    )
    PARAMETERS = {}

    def compute(self, session: Any, user: User, kwargs: dict[str, Any]) -> dict[str, Any]:
        from onyx.db.ton import agent_actions

        rules = agent_actions.rules_for_chat(session)
        return {"kind": "controller_rules", "total": len(rules), "regras": rules}


class TonProposeLedgerTool(TonProposeActionTool):
    NAME = "ton_propose_ledger_registration"
    KIND = ActionKind.LEDGER_REGISTER
    PAYLOAD = LedgerRegisterPayload
    DESCRIPTION = (
        "Propor registrar no ledger de ocorrências os casos de um teste (T1, T2, T3, T4, T6, T8, T9, T10). "
        "Passe o teste, os mesmos test_parameters usados ao rodá-lo e as chaves (campo chave de cada item) dos "
        "casos escolhidos; sem chaves, registra todos. O servidor roda o teste de novo e sugere a criticidade "
        "pela régua PAD-CTRL-001 (impacto ÷ receita da unidade no mês). Pode já atribuir responsável, prazo e nota. "
        "Caso já registrado conta como repetição, sem duplicar."
    )


class TonProposeOccurrenceAssignTool(TonProposeActionTool):
    NAME = "ton_propose_occurrence_assignment"
    KIND = ActionKind.OCCURRENCE_ASSIGN
    PAYLOAD = OccurrenceAssignPayload
    DESCRIPTION = (
        "Propor responsável (nome ou cargo), prazo e/ou nota para ocorrências do ledger (ids de "
        "ton_list_occurrences ou de um registro recente). Não invente responsáveis: use o que a pessoa disser."
    )


class TonProposeR1Tool(TonProposeActionTool):
    NAME = "ton_propose_daily_sweep"
    KIND = ActionKind.R1_SCHEDULE
    PAYLOAD = R1SchedulePayload
    DESCRIPTION = (
        "Propor ligar ou desligar a varredura diária R1: todo dia o TON roda os testes escolhidos no último "
        "mês e registra os casos no ledger com a criticidade da régua PAD-CTRL-001. A pessoa aprova testes, "
        "horário e faixas ao aplicar."
    )


class TonR1StatusTool(TonFunctionTool):
    NAME = "ton_get_daily_sweep"
    DESCRIPTION = "Ver se a varredura diária R1 está ligada, seu horário, testes e as últimas execuções."
    PARAMETERS = {}

    def compute(self, session: Any, user: User, kwargs: dict[str, Any]) -> dict[str, Any]:
        from onyx.db.ton import agent_ledger
        from onyx.ton.automations import service as automation_service

        automation = agent_ledger.r1_automation(session)
        if automation is None:
            return {"kind": "daily_sweep", "ligada": False, "configurada": False}
        detail = automation_service.detail(session, user, automation.id)
        data = detail.model_dump(mode="json")
        return {
            "kind": "daily_sweep",
            "ligada": automation.status == "ACTIVE",
            "situacao": automation.status,
            "link": f"/ton/automacoes/{automation.id}",
            "quando": data.get("when") or data.get("schedule"),
            "execucoes": (data.get("runs") or [])[:5],
        }


class TonClassificationQueueTool(TonFunctionTool):
    NAME = "ton_list_classification_queue"
    DESCRIPTION = (
        "Listar contas do NG sem natureza ou aguardando confirmação, com a sugestão do assistente, número de "
        "lançamentos e valor, e as naturezas disponíveis. Com status=ALL e compact=true, devolve o plano inteiro "
        "(conta, nome, natureza atual e grupo da DRE): use para comparar com uma estrutura de BI."
    )
    PARAMETERS = {
        "status": {
            "type": "string",
            "enum": ["PENDING", "AWAITING_CONFIRMATION", "CONFIRMED", "ALL"],
            "description": "Padrão: pendentes e aguardando confirmação.",
        },
        "text": {"type": "string", "description": "Filtro pelo código ou descrição da conta."},
        "compact": {
            "type": "boolean",
            "description": "Todas as contas, só conta, nome, natureza e grupo (sem valores).",
        },
    }

    def compute(self, session: Any, user: User, kwargs: dict[str, Any]) -> dict[str, Any]:
        from onyx.db.ton import account_classification

        table = account_classification.classification_table(session, user, None)
        groups = {item.natureza: item.dre_group for item in table.natures}
        status = kwargs.get("status")
        text = str(kwargs.get("text") or "").lower()
        rows = [
            row
            for row in table.rows
            if (
                status == "ALL"
                or (status and row.status.value == status)
                or (not status and row.status.value != "CONFIRMED")
            )
            and (not text or text in f"{row.account_code} {row.description}".lower())
        ]
        rows.sort(key=lambda row: -abs(row.total_amount))
        if kwargs.get("compact"):
            rows.sort(key=lambda row: row.account_code)
            return {
                "kind": "classification_plan",
                "total": len(rows),
                "contas": [
                    [row.account_code, row.description, row.natureza, groups.get(row.natureza or "")]
                    for row in rows[:400]
                ],
                "colunas": ["conta", "nome", "natureza", "grupo"],
                "naturezas": [f"{item.code} {item.natureza} ({item.dre_group})" for item in table.natures],
                "grupos": [f"{item.code} {item.label}" for item in table.groups],
            }
        return {
            "kind": "classification_queue",
            "total": len(rows),
            "contas": [
                {
                    "conta": row.account_code,
                    "descricao": row.description,
                    "situacao": row.status.value,
                    "natureza_atual": row.natureza,
                    "sugestao": row.suggestion.model_dump(mode="json") if row.suggestion else None,
                    "lancamentos": row.entries,
                    "valor": str(row.total_amount),
                    "unidades": row.units[:6],
                }
                for row in rows[:40]
            ],
            "naturezas": [f"{item.code} {item.natureza} ({item.dre_group})" for item in table.natures],
        }


class TonUnitMissingTool(TonFunctionTool):
    NAME = "ton_list_unit_missing"
    DESCRIPTION = "Listar lançamentos do NG sem unidade (abertos), com o id da pendência e as linhas da planilha."
    PARAMETERS = {
        "include_decided": {"type": "boolean", "description": "Incluir os já atribuídos."}
    }

    def compute(self, session: Any, user: User, kwargs: dict[str, Any]) -> dict[str, Any]:
        from onyx.db.ton import unit_assignment

        items = unit_assignment.list_unit_missing(session, user)
        if not kwargs.get("include_decided"):
            items = [item for item in items if item.open]
        return {
            "kind": "unit_missing",
            "total": len(items),
            "itens": [item.model_dump(mode="json") for item in items[:40]],
        }


class TonListAutomationsTool(TonFunctionTool):
    NAME = "ton_list_automations"
    DESCRIPTION = "Listar as automações (nome, tipo, situação, gatilho, últimas execuções)."
    PARAMETERS = {}

    def compute(self, session: Any, user: User, kwargs: dict[str, Any]) -> dict[str, Any]:
        from onyx.ton.automations import service as automation_service

        table = automation_service.table(session, user)
        return {"kind": "automations", **table.model_dump(mode="json")}


_OPEN_TITLE_STATUSES = {
    "WAITING_ATTACHMENT",
    "WAITING_SUPPLIER",
    "RECEIVED",
    "RETURNED",
    "CONFERRED",
    "RELEASED",
}
_TITLE_VIEWS = ("abertos", "vencidos", "vencem_7_dias", "impedimento", "prontos", "todos")


class TonPayablesTool(TonFunctionTool):
    NAME = "ton_list_payables"
    DESCRIPTION = (
        "Agenda de contas a pagar das unidades: títulos com fornecedor, unidade, natureza, valor, vencimento, "
        "situação e o que o TON apontou (impedimentos). Use para 'o que vence esta semana', 'o que dá para pagar "
        "hoje', 'o que está travado', 'títulos do fornecedor X'. Com title_number devolve o detalhe de um título "
        "(CP-000004 ou 4), incluindo as conferências."
    )
    PARAMETERS = {
        "view": {
            "type": "string",
            "enum": list(_TITLE_VIEWS),
            "description": "abertos (padrão), vencidos, vencem_7_dias, impedimento, prontos (liberados) ou todos.",
        },
        "supplier": {"type": "string", "description": "Nome, CNPJ ou parte do nome do fornecedor."},
        "unit": UNIT,
        "title_number": {"type": "string", "description": "Número do título (CP-000004 ou 4) para o detalhe."},
    }

    def compute(self, session: Any, user: User, kwargs: dict[str, Any]) -> dict[str, Any]:
        from onyx.db.ton import payables as payables_service

        today = datetime.date.today()
        rows = payables_service.list_titles(
            session, user, None, None, kwargs.get("supplier") or None, None, None, 2000
        )
        number = str(kwargs.get("title_number") or "").upper().replace("CP-", "").strip()
        if number:
            match = next((row for row in rows if str(row.number) == number.lstrip("0")), None)
            if match is None:
                raise ValueError(f"Título {kwargs.get('title_number')} não encontrado")
            detail = payables_service.get_title(session, user, match.id)
            return {"kind": "payable_title", "today": today.isoformat(), "titulo": detail.model_dump(mode="json")}
        unit = str(kwargs.get("unit") or "").strip().lower()
        if unit:
            rows = [row for row in rows if unit in row.unit_name.lower()]
        open_rows = [row for row in rows if row.kind == "REAL" and row.status in _OPEN_TITLE_STATUSES]
        views = {
            "abertos": [row for row in rows if row.status in _OPEN_TITLE_STATUSES or row.status == "ESTIMATE_OPEN"],
            "vencidos": [row for row in open_rows if row.due_date < today],
            "vencem_7_dias": [row for row in open_rows if 0 <= (row.due_date - today).days <= 7],
            "impedimento": [row for row in open_rows if row.blocking > 0],
            "prontos": [row for row in rows if row.status == "RELEASED"],
            "todos": rows,
        }
        view = kwargs.get("view") or "abertos"
        if view not in views:
            raise ValueError("Visão desconhecida")
        chosen = sorted(views[view], key=lambda row: (row.due_date, row.number))

        def total(items: list[Any]) -> str:
            return str(sum((row.amount for row in items), Decimal("0")))

        return {
            "kind": "payables",
            "today": today.isoformat(),
            "view": view,
            "resumo": {name: {"titulos": len(items), "valor": total(items)} for name, items in views.items()},
            "titulos": [
                {
                    "numero": f"CP-{row.number:06d}",
                    "fornecedor": row.supplier_name,
                    "cnpj": row.supplier_tax_id,
                    "unidade": row.unit_name,
                    "natureza": f"{row.account_code} {row.account_label}",
                    "documento": f"{row.document_type or ''} {row.document_number or ''}".strip(),
                    "placas": row.vehicle_plates,
                    "valor": str(row.amount),
                    "vencimento": row.due_date.isoformat(),
                    "dias_para_vencer": (row.due_date - today).days,
                    "situacao": row.status,
                    "pagar_por": row.payment_method,
                    "anexos": row.attachment_count,
                    "impedimentos": row.blocking,
                    "atencoes": row.attention,
                    "ton_apontou": row.top_issue,
                }
                for row in chosen[:60]
            ],
            "mais": max(0, len(chosen) - 60),
        }

TON_TOOL_CLASSES = (
    TonListSourcesTool,
    TonGetSourceStatusTool,
    TonListFindingsTool,
    TonGetFindingTool,
    TonFinancialReviewSummaryTool,
    TonDreReadinessTool,
    TonDreResultTool,
    TonFinancialContextTool,
    TonClosingOverviewTool,
    TonAnalyzeClosingTool,
    TonClosingReportTool,
    TonExecutiveBriefTool,
    TonBillingSummaryTool,
    TonBudgetSummaryTool,
    TonReconciliationSummaryTool,
    TonListOccurrencesTool,
    TonGetOccurrenceTool,
    TonOverdueActionsTool,
    TonReadinessEvidenceTool,
    TonRecentChangesTool,
    TonDraftAutomationTool,
    TonDreStructureTool,
    TonProposeStructureChangeTool,
    TonProposeStructureCreateTool,
    TonProposeAdjustmentTool,
    TonProposeTreatmentTool,
    TonProposeRecalculationTool,
    TonProposeImportTool,
    TonSearchEntriesTool,
    TonSupplierSummaryTool,
    TonFinancialTestTool,
    TonCompareDreTool,
    TonLineEntriesTool,
    TonProposeClassificationTool,
    TonProposeClassificationConfirmTool,
    TonProposeReviewDecisionTool,
    TonProposeUnitAssignmentTool,
    TonProposeAutomationStatusTool,
    TonProposeAutomationRunTool,
    TonClassificationQueueTool,
    TonUnitMissingTool,
    TonListAutomationsTool,
    TonProposeControllerRuleTool,
    TonControllerRulesTool,
    TonProposeLedgerTool,
    TonProposeOccurrenceAssignTool,
    TonProposeR1Tool,
    TonR1StatusTool,
    TonPayablesTool,
)
