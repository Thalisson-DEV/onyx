"""Prompt Mestre coverage definitions; registration never activates a rule."""

from typing import Literal

from pydantic import BaseModel

CapabilityStatus = Literal["OPERATIONAL", "PARTIAL", "BLOCKED", "NOT_IMPLEMENTED"]


class CapabilityView(BaseModel):
    key: str
    name: str
    family: str
    status: CapabilityStatus
    status_label: str
    reason: str
    required_sources: list[str]
    required_configuration: list[str]
    owner_specialist: str
    next_dependency: str


# Business names from Prompt Mestre v2, sections 6-8. No thresholds are activated.
SANITY_RULES = (
    ("S1", "Sanidade da margem contratual", "CFO", "contratos e DRE"),
    ("S2", "Saldo e prazo a realizar", "CONTRATOS", "contratos e backlog"),
    ("S3", "Resultado projetado", "CFO", "contratos e backlog"),
    ("S4", "Soma das linhas e subtotal", "AUDITOR", "base financeira"),
    ("S5", "Unidades e consolidado", "AUDITOR", "base financeira e unidades"),
    ("S6", "Sinal por natureza", "CFO", "base financeira e plano gerencial"),
    ("S7", "Contrato assinado no backlog", "CONTRATOS", "contratos e backlog"),
    ("S8", "Análise vertical por unidade", "CFO", "DRE por unidade"),
    ("S9", "Comparabilidade da unidade de medida", "COO", "produção e serviços"),
    ("S10", "Bloqueio de margem sobre base inválida", "CFO", "prontidão financeira"),
)

FINANCIAL_TESTS = (
    ("T1", "Grupo zerado", "CFO", "base financeira e grupos contratuais"),
    ("T2", "Desvio de média móvel", "CFO", "histórico financeiro por unidade"),
    ("T3", "Duplicidade", "AUDITOR", "notas fiscais e fornecedores"),
    ("T4", "Receita NF e NG", "CFO", "NG e faturamento"),
    ("T5", "Receita replicada", "CFO", "histórico financeiro por unidade"),
    ("T6", "Sinal invertido", "CFO", "base financeira e plano gerencial"),
    ("T7", "Pagamento sem apropriação", "CFO", "pagamentos e classificações"),
    ("T8", "Fornecedor e unidade", "AUDITOR", "fornecedores e unidades"),
    ("T9", "Competência retroativa", "CFO", "documentos e competência"),
    ("T10", "Evento não recorrente", "CFO", "lançamentos e despesas do mês"),
    ("T11", "Partes relacionadas", "CFO", "pagamentos e partes relacionadas"),
    ("T12", "Rescisão e multa FGTS", "RH", "folha e verbas rescisórias"),
)

OPERATIONAL_TESTS = (
    ("T13", "Execução e medição", "COO", "produção e medição"),
    ("T14", "Medição e faturamento", "CONTRATOS", "medição e faturamento"),
    ("T15", "Faturamento sem lastro", "CONTRATOS", "produção e faturamento"),
    (
        "T16",
        "Produção sem faturamento",
        "CONTRATOS",
        "contratos, produção e faturamento",
    ),
    ("T17", "Reajuste não incorporado", "CONTRATOS", "contratos e faturamento"),
    ("T18", "Saldo contratual", "CONTRATOS", "contratos e execução"),
    ("T19", "Vigência contratual", "CONTRATOS", "contratos"),
    ("T20", "Recebimento", "CFO", "faturamento e recebíveis"),
    ("T21", "Consumo anômalo", "FROTA", "frota e abastecimento"),
    ("T22", "Abastecimento inconsistente", "FROTA", "frota, abastecimento e produção"),
    ("T23", "Manutenção e margem", "FROTA", "manutenção e reposição de frota"),
    ("T24", "Frota prevista e real", "FROTA", "dotação e frota"),
    ("T25", "Produtividade", "COO", "produção, equipes e dotação"),
    ("T26", "Custo unitário comparado", "COO", "custos e produção por serviço"),
    ("T27", "Quadro e dotação", "RH", "pessoal e dotação"),
    ("T28", "Afastamento e reserva técnica", "RH", "pessoal e reserva contratual"),
    ("T29", "Horas extras", "RH", "ponto e folha"),
    ("T30", "Preço de compra", "COMPRAS", "compras e histórico de preços"),
)

STATUS_LABELS: dict[str, str] = {
    "OPERATIONAL": "Operacional",
    "PARTIAL": "Parcial",
    "BLOCKED": "Bloqueada",
    "NOT_IMPLEMENTED": "Não implementada",
}


def rule_capabilities() -> list[CapabilityView]:
    result = []
    for key, name, owner, source in (
        *SANITY_RULES,
        *FINANCIAL_TESTS,
        *OPERATIONAL_TESTS,
    ):
        status: CapabilityStatus = "NOT_IMPLEMENTED"
        reason = "Executor específico do Prompt Mestre ainda não habilitado. A revisão NG não equivale a este teste."
        dependency = (
            "Validar campos, configuração e executor determinístico desta regra."
        )
        if key == "S10":
            status = "OPERATIONAL"
            reason = "A DRE pendente não retorna resultado oficial. O fechamento não estima margem nem valores."
            dependency = (
                "Resolver bloqueios de prontidão antes de publicar valores oficiais."
            )
        elif key == "T4":
            status = "PARTIAL"
            reason = "Conciliação NG e faturamento disponível. O teste de divergência por unidade do Prompt Mestre ainda não está habilitado."
            dependency = "Aprovar vínculos, semântica de valor e configuração do teste por unidade."
        result.append(
            CapabilityView(
                key=key,
                name=name,
                family="Sanidade"
                if key.startswith("S")
                else "Testes financeiros"
                if int(key[1:]) <= 12
                else "Testes operacionais e contratuais",
                status=status,
                status_label=STATUS_LABELS[status],
                reason=reason,
                required_sources=[source],
                required_configuration=["Campos e parâmetros da regra aprovados"],
                owner_specialist=owner,
                next_dependency=dependency,
            )
        )
    return result
