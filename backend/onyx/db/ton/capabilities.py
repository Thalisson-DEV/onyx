"""Current coverage built from shared closing and existing source services."""

from sqlalchemy.orm import Session

from onyx.db.models import User
from onyx.db.ton.closing import inspect_closing
from onyx.ton.agent.capabilities import (
    STATUS_LABELS,
    CapabilityStatus,
    CapabilityView,
    rule_capabilities,
)
from onyx.ton.agent.closing_models import ClosingRequest
from onyx.ton.agent.registry import ROUTINES, SPECIALISTS


def capability_registry(
    session: Session, user: User, request: ClosingRequest
) -> list[CapabilityView]:
    output = inspect_closing(session, user, request)
    result = rule_capabilities()
    for definition in SPECIALISTS:
        outcome = next(
            item for item in output.specialists if item.key == definition.key
        )
        status: CapabilityStatus = (
            "OPERATIONAL"
            if outcome.status == "Operacional"
            else "PARTIAL"
            if outcome.status == "Parcial"
            else "BLOCKED"
        )
        result.append(
            CapabilityView(
                key=definition.key,
                name=definition.name,
                family="Especialistas",
                status=status,
                status_label=STATUS_LABELS[status],
                reason=outcome.reason,
                required_sources=definition.required_capabilities,
                required_configuration=[definition.autonomy_policy],
                owner_specialist=definition.name,
                next_dependency="; ".join(
                    outcome.limitations or definition.required_capabilities
                ),
            )
        )
    for key, name, reason in ROUTINES:
        status = "PARTIAL" if key == "R3" else "BLOCKED"
        result.append(
            CapabilityView(
                key=key,
                name=name,
                family="Rotinas",
                status=status,
                status_label=STATUS_LABELS[status],
                reason="Execução manual e publicação persistida disponíveis. Agendamento não configurado."
                if key == "R3"
                else reason,
                required_sources=[reason],
                required_configuration=[
                    "Calendário, escopo e destinatários autorizados"
                ],
                owner_specialist="CFO / AUDITOR / CEO"
                if key == "R3"
                else "A definir na configuração da rotina",
                next_dependency="Configurar agendamento e limites de publicação."
                if key == "R3"
                else reason,
            )
        )
    sources = {str(item["key"]): item for item in output.sources}
    for key, name, import_key, owner in (
        ("SOURCE_NG", "NG / Keevo", "financial_launches", "CFO"),
        ("SOURCE_CONTRACTS", "Contratos", None, "CONTRATOS"),
        ("SOURCE_BUDGET", "Dotação / Orçamento", "budget", "CFO"),
        ("SOURCE_BACKLOG", "Backlog", None, "CONTRATOS"),
        ("SOURCE_FLEET", "Frota", None, "FROTA"),
        ("SOURCE_FUEL", "Abastecimento", None, "FROTA"),
        ("SOURCE_PRODUCTION", "Produção", None, "COO"),
        ("SOURCE_PERSONNEL", "Pessoal", None, "RH"),
        (
            "SOURCE_BILLING",
            "Medição / Faturamento",
            "billing_invoices",
            "CFO / CONTRATOS",
        ),
        ("SOURCE_ZEEV", "Zeev / Contexto de processos", None, "AUDITOR"),
    ):
        source = sources.get(import_key) if import_key else None
        status = "PARTIAL" if source or key == "SOURCE_ZEEV" else "BLOCKED"
        reason = "Fonte operacional ainda não integrada. Nenhum resultado deste domínio foi calculado."
        dependency = "Validar esquema, origem e acesso autorizado desta família."
        if source:
            reason = (
                str(source["status"])
                + ". Aquisição por arquivo. Integração direta não configurada."
            )
            dependency = (
                "Confirmar cobertura, mapeamentos e decisões da base importada."
            )
            if key == "SOURCE_NG":
                reason = (
                    str(source["status"])
                    + ". Importação manual disponível; integração direta aguarda acesso e configuração."
                )
                dependency = "Obter acesso direto autorizado, documentação e usuário técnico de leitura."
            elif key == "SOURCE_BILLING":
                dependency = "Integrar medição e recebimento; faturamento por arquivo já é suportado."
        elif key == "SOURCE_ZEEV":
            reason = "Fundação de leitura e descoberta disponível no código. Sincronização operacional e conexão atual não validadas."
            dependency = "Confirmar fluxos, campos, estados e significado dos prazos com o responsável."
        result.append(
            CapabilityView(
                key=key,
                name=name,
                family="Fontes",
                status=status,
                status_label=STATUS_LABELS[status],
                reason=reason,
                required_sources=[name],
                required_configuration=[
                    "Esquema, escopo e acesso de leitura autorizados"
                ],
                owner_specialist=owner,
                next_dependency=dependency,
            )
        )
    return result
