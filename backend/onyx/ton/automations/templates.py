"""Starting points shown in "Nova automação". Each one is a complete
definition that passes the checker once recipients are filled in."""

from dataclasses import dataclass
from typing import Any

from onyx.ton.automations.definition import AutomationKind

WEEKLY_BODY = (
    "<p>Olá,</p>"
    "<p>Estas são as inconsistências do NG que ainda precisam de correção, agrupadas por unidade, "
    "com o que fazer em cada uma.</p>"
    '<div data-block="summary"></div>'
    '<div data-block="inconsistency_table"></div>'
    "<p>Assim que forem corrigidas no NG, o TON confere na próxima extração e elas saem desta lista.</p>"
    '<div data-block="ton_button"></div>'
)


@dataclass(frozen=True)
class Template:
    key: str
    name: str
    description: str
    kind: AutomationKind
    definition: dict[str, Any]


TEMPLATES: tuple[Template, ...] = (
    Template(
        "weekly_inconsistencies",
        "Relatório semanal de inconsistências",
        "Toda segunda às 08:00, envia ao Financeiro as inconsistências do NG ainda abertas, por unidade.",
        AutomationKind.EMAIL,
        {
            "schema": 3,
            "trigger": {"type": "trigger.schedule", "params": {"frequency": "week", "weekdays": [0], "time": "08:00"}},
            "steps": [
                {"id": "buscar", "type": "ton.inconsistencies", "label": "Buscar inconsistências abertas", "params": {}},
                {
                    "id": "tem_itens",
                    "type": "control.condition",
                    "label": "Há inconsistências abertas?",
                    "params": {"condition": {"op": "and", "rules": [{"left": "{{ steps.buscar.outputs.count }}", "operator": "gt", "right": "0"}]}},
                    "then": [
                        {
                            "id": "email",
                            "type": "email.send",
                            "label": "Enviar ao Financeiro",
                            "params": {
                                "to": [],
                                "subject": "Inconsistências do NG – semana {{ trigger.outputs.semana }} ({{ steps.buscar.outputs.count }})",
                                "body": WEEKLY_BODY,
                                "items": "{{ steps.buscar.outputs.items }}",
                            },
                        }
                    ],
                    "else": [],
                },
            ],
        },
    ),
    Template(
        "big_inconsistency_alert",
        "Alerta de inconsistência alta",
        "Quando uma importação traz inconsistência nova acima de R$ 100 mil, avisa no TON e por e-mail.",
        AutomationKind.ALERT,
        {
            "schema": 3,
            "trigger": {"type": "trigger.ng_occurrence_changed", "params": {"changes": ["NEW", "REAPPEARED"]}},
            "variables": [{"name": "limite", "type": "number", "value": 100000, "description": "Valor a partir do qual avisar"}],
            "steps": [
                {
                    "id": "altas",
                    "type": "data.filter",
                    "label": "Só as acima do limite",
                    "params": {
                        "items": "{{ trigger.outputs.items }}",
                        "condition": {"op": "and", "rules": [{"left": "{{ item.valor }}", "operator": "gte", "right": "{{ vars.limite }}"}]},
                    },
                },
                {
                    "id": "tem_altas",
                    "type": "control.condition",
                    "label": "Alguma acima do limite?",
                    "params": {"condition": {"op": "and", "rules": [{"left": "{{ steps.altas.outputs.count }}", "operator": "gt", "right": "0"}]}},
                    "then": [
                        {
                            "id": "aviso",
                            "type": "ton.notify",
                            "label": "Avisar no TON",
                            "params": {
                                "title": "{{ steps.altas.outputs.count }} inconsistência(s) acima de {{ format_money(vars.limite) }}",
                                "message": "Total {{ steps.altas.outputs.total_formatado }}. {{ trigger.outputs.note }}",
                                "severity": "CRITICAL",
                                "link": "/ton/pendencias",
                            },
                        },
                        {
                            "id": "email",
                            "type": "email.send",
                            "label": "Enviar à Controladoria",
                            "params": {
                                "to": [],
                                "subject": "Inconsistência alta no NG: {{ steps.altas.outputs.total_formatado }}",
                                "body": '<p>Olá,</p><p>A última importação do NG trouxe inconsistências acima do limite combinado.</p><div data-block="inconsistency_table"></div><div data-block="ton_button"></div>',
                                "items": "{{ steps.altas.outputs.items }}",
                            },
                        },
                    ],
                    "else": [],
                },
            ],
        },
    ),
    Template(
        "ai_summary_after_import",
        "Resumo com IA após a importação",
        "Ao terminar uma importação do NG, a IA resume as inconsistências abertas e o resumo vai por e-mail.",
        AutomationKind.DATA_AI,
        {
            "schema": 3,
            "trigger": {"type": "trigger.ng_import", "params": {}},
            "steps": [
                {
                    "id": "resumo",
                    "type": "ai.summarize",
                    "label": "Resumir para a diretoria",
                    "params": {"input": "{{ trigger.outputs.by_unit }}", "style": "executive", "max_lines": 7},
                },
                {
                    "id": "email",
                    "type": "email.send",
                    "label": "Enviar resumo",
                    "params": {
                        "to": [],
                        "subject": "Resumo da importação do NG – {{ trigger.outputs.open_count }} abertas",
                        "body": '<p>Olá,</p><p><span data-expr="steps.resumo.outputs.text"></span></p><div data-block="summary"></div><div data-block="ton_button"></div>',
                        "items": "{{ trigger.outputs.items }}",
                    },
                },
            ],
        },
    ),
    Template(
        "document_intake",
        "Ler documento e registrar",
        "Alguém envia um documento (PDF, Excel, texto); a IA extrai os campos, uma pessoa aprova e o TON avisa a equipe.",
        AutomationKind.APPROVAL,
        {
            "schema": 3,
            "trigger": {
                "type": "trigger.manual",
                "params": {"inputs": [{"name": "texto", "label": "Cole o texto do documento", "type": "longtext", "required": True}]},
            },
            "steps": [
                {
                    "id": "extrair",
                    "type": "ai.extract",
                    "label": "Extrair os dados",
                    "params": {
                        "input": "{{ trigger.outputs.inputs.texto }}",
                        "fields": [
                            {"name": "fornecedor", "type": "text", "description": "Razão social do fornecedor"},
                            {"name": "valor", "type": "number", "description": "Valor total em reais"},
                            {"name": "vencimento", "type": "date", "description": "Data de vencimento"},
                        ],
                    },
                },
                {
                    "id": "aprovar",
                    "type": "approval.request",
                    "label": "Conferir os dados",
                    "params": {
                        "approvers": [],
                        "title": "Os dados extraídos estão certos?",
                        "details": "Fornecedor: {{ steps.extrair.outputs.fields.fornecedor }}\nValor: {{ format_money(steps.extrair.outputs.fields.valor) }}\nVencimento: {{ steps.extrair.outputs.fields.vencimento }}",
                    },
                },
                {
                    "id": "aprovado",
                    "type": "control.condition",
                    "label": "Aprovado?",
                    "params": {"condition": {"op": "and", "rules": [{"left": "{{ steps.aprovar.outputs.approved }}", "operator": "is_true", "right": ""}]}},
                    "then": [
                        {
                            "id": "aviso",
                            "type": "ton.notify",
                            "label": "Avisar no TON",
                            "params": {"title": "Documento de {{ steps.extrair.outputs.fields.fornecedor }} conferido", "message": "Valor {{ format_money(steps.extrair.outputs.fields.valor) }}", "severity": "INFO"},
                        }
                    ],
                    "else": [],
                },
            ],
        },
    ),
    Template(
        "unclassified_accounts",
        "Contas novas sem classificação",
        "Ao terminar uma importação com contas sem natureza confirmada, envia a lista à Controladoria.",
        AutomationKind.EMAIL,
        {
            "schema": 3,
            "trigger": {"type": "trigger.account_unclassified", "params": {"skip_when_empty": True}},
            "steps": [
                {
                    "id": "email",
                    "type": "email.send",
                    "label": "Enviar a lista",
                    "params": {
                        "to": [],
                        "subject": "{{ trigger.outputs.count }} conta(s) do NG sem classificação",
                        "body": '<p>Olá,</p><p>Estas contas ainda não têm natureza confirmada no TON:</p><div data-block="account_table"></div><div data-block="ton_button"></div>',
                        "items": "{{ trigger.outputs.items }}",
                        "link": "/ton/classificacao",
                    },
                }
            ],
        },
    ),
    Template(
        "failure_watch",
        "Avisar quando uma automação falhar",
        "Quando qualquer automação termina com falha, avisa no TON e manda e-mail a quem cuida.",
        AutomationKind.ALERT,
        {
            "schema": 3,
            "trigger": {"type": "trigger.automation_failed", "params": {"automations": []}},
            "steps": [
                {
                    "id": "aviso",
                    "type": "ton.notify",
                    "label": "Avisar no TON",
                    "params": {"title": "Falhou: {{ trigger.outputs.automation_name }}", "message": "{{ trigger.outputs.error }}", "severity": "WARNING", "link": "{{ trigger.outputs.link }}"},
                }
            ],
        },
    ),
)
