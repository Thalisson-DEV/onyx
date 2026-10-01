"""Business labels for agent output; internal service codes stay unchanged."""

import re
from typing import Any

LABELS = {
    "NEW": "Nova",
    "REOPENED": "Reaberta",
    "CONFIRMED": "Confirmada",
    "RESOLVED": "Resolvida",
    "RISK_ACCEPTED": "Risco aceito",
    "DISMISSED": "Dispensada",
    "SUPERSEDED": "Substituída",
    "OPEN": "Aberta",
    "CANCELLED": "Cancelada",
    "CRITICAL": "Crítica",
    "HIGH": "Alta",
    "MEDIUM": "Média",
    "LOW": "Baixa",
    "ACTIVE": "Ativa",
    "FILE_UPLOAD": "Envio de arquivo",
    "CURRENT": "Importação concluída",
    "PROCESSING": "Em processamento",
    "ATTENTION": "Requer atenção",
    "FORMULA_DENOMINATOR_ZERO": "Denominador da fórmula igual a zero",
    "DRE_STRUCTURE_INVALID": "Estrutura DRE inválida",
    "INGESTION": "Consulta das fontes",
    "BASE_VALIDATION": "Validação da base",
    "CHAIN_RECONCILIATION": "Conciliação",
    "DETECTION": "Detecção",
    "QUANTIFICATION": "Quantificação",
    "PRIORITIZATION": "Priorização",
    "PUBLICATION": "Publicação",
    "UNCONFIGURED": "Não configurada",
    "NO_IMPORT": "Sem importação",
    "IMPORTED": "Importada",
    "AVAILABLE": "Disponível",
    "UNMAPPED_ACCOUNT": "Conta não vinculada",
    "UNMAPPED_UNIT": "Unidade não vinculada",
    "UNCLASSIFIED_ACCOUNT": "Conta sem classificação financeira",
    "BUDGET_UNMAPPED_ACCOUNT": "Conta do orçamento não vinculada",
    "BUDGET_UNMAPPED_UNIT": "Unidade do orçamento não vinculada",
    "REVIEW_UNRESOLVED": "Revisão financeira pendente",
    "EXCLUDED_SOURCE_ROWS": "Linhas excluídas por erro na fonte",
    "BILLING_COMPETENCE_UNRESOLVED": "Competência do faturamento não definida",
    "UNSUPPORTED_DERIVATION": "Derivação financeira não suportada",
    "IR_RETENTION_UNRESOLVED": "Retenção de imposto não definida",
    "ACTUAL_AMOUNT_SEMANTICS_UNRESOLVED": "Base de valor realizado não definida",
    "MISSING_BUDGET": "Orçamento ausente no escopo",
    "SOURCE_RECONCILIATION_AMBIGUOUS": "Conciliação ambígua",
    "SOURCE_RECONCILIATION_UNRESOLVED": "Conciliação sem decisão",
    "NO_ACTUAL": "Períodos sem realizado no escopo",
    "DRE_MAPPING_PENDING_APPROVAL": "Classificação DRE aguarda aprovação",
    "ACTUAL_UNIT_SCOPE_UNRESOLVED": "Escopo da unidade não definido",
    "MATCHED": "Conciliado",
    "AMBIGUOUS": "Correspondência ambígua",
    "UNMAPPED": "Sem vínculo",
    "UNMATCHED": "Sem correspondência",
    "READY": "Pronta",
    "NOT_READY": "Pendente",
    "UNKNOWN": "Não verificado",
    "SUCCEEDED": "Concluído",
    "PARTIAL": "Parcial",
    "FAILED": "Falhou",
    "RUNNING": "Em execução",
    "QUEUED": "Na fila",
    "PENDING": "Pendente",
    "COMPLETED": "Concluído",
    "COMPLETED_WITH_BLOCKED_DOMAINS": "Concluído com bloqueios",
    "PASSED": "Concluído",
    "BLOCKED": "Bloqueado",
    "SKIPPED": "Não executado",
    "ACCEPTED": "Revisado",
    "REVIEW_REQUIRED": "Revisão necessária",
    "CORRECTION_REQUIRED": "Correção necessária",
    "EXCLUDED_SOURCE_ERROR": "Excluído por erro na fonte",
    "JUSTIFIED_EXCEPTION": "Exceção justificada",
    "SUPERSEDED_BY_CORRECTION": "Substituído por correção",
    "DRE_ACCOUNT_UNMAPPED": "Conta sem classificação na DRE",
    "UNIT_UNMAPPED": "Unidade não vinculada",
    "ACCOUNT_UNMAPPED": "Conta não vinculada",
    "AMOUNT_BASIS_UNRESOLVED": "Base de valor não definida",
    "BUDGET_PERIOD_UNRESOLVED": "Período do orçamento não definido",
    "RECONCILIATION_UNRESOLVED": "Conciliação pendente",
    "RECONCILIATION_PENDING": "Conciliação pendente",
    "BASE_REPROVED": "Base reprovada para publicação financeira",
    "MISSING_SOURCE": "Fonte necessária ausente",
    "AWAITING_HUMAN_DECISION": "Aguardando decisão humana",
    "PREREQUISITE_FAILED": "Etapa anterior pendente",
    "NOT_REQUIRED": "Não necessário",
}


def business_label(code: str) -> str:
    return LABELS.get(
        code,
        LABELS.get(
            code.upper(),
            re.sub(r"\bSynthetic unit\b", "Unidade de demonstração", code, flags=re.I),
        ),
    )


def humanize(value: Any) -> Any:
    if isinstance(value, dict):
        return {business_label(str(key)): humanize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [humanize(item) for item in value]
    return business_label(value) if isinstance(value, str) else value
