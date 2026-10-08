"""Approval step. The interpreter suspends the run until a person decides
(or the deadline passes); the outcome is an output, so a following
condition or switch routes on it."""

from onyx.ton.automations.definition import AutomationKind
from onyx.ton.automations.registry import NodeSpec, OutputSpec, ParamSpec, register

register(
    NodeSpec(
        type="approval.request",
        group="approval",
        label="Pedir aprovação",
        description="Para a execução até alguém do TON aprovar, recusar ou escolher uma opção. As pessoas recebem e-mail com o link.",
        icon="check",
        params=(
            ParamSpec("approvers", "Quem aprova (e-mails)", "emails", required=True, default=[]),
            ParamSpec("title", "Título", "text", required=True, placeholder="Enviar o relatório ao Financeiro?"),
            ParamSpec("details", "Detalhes", "textarea", placeholder="{{ steps.resumo.outputs.text }}"),
            ParamSpec("kind", "Respostas", "select", default="approve_reject", dynamic=False, options=(("approve_reject", "Aprovar / Recusar"), ("custom", "Opções próprias"))),
            ParamSpec("options", "Opções", "list", default=[], show_if=("kind", ("custom",))),
            ParamSpec("expires_after_hours", "Prazo em horas (0 = sem prazo)", "number", default=0, min=0, max=2160),
        ),
        outputs=(
            OutputSpec("outcome", "Resposta (Aprovar, Recusar ou a opção)", "string"),
            OutputSpec("approved", "Aprovado", "boolean"),
            OutputSpec("responder", "Quem respondeu", "string"),
            OutputSpec("comment", "Comentário", "string"),
            OutputSpec("decided_at", "Quando", "string"),
        ),
        satisfies=(AutomationKind.APPROVAL,),
        keywords=("aprovar", "autorizar", "decisão", "humano"),
    )
)
