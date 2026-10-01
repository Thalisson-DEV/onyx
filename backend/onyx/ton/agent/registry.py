"""Specialist configuration, separate from current source availability."""

from onyx.ton.agent.closing_models import SpecialistDefinition

SPECIALISTS = (
    SpecialistDefinition(
        key="CFO",
        name="TON CFO",
        objective="Identificar pendências do fechamento financeiro.",
        domain="FINANCIAL",
        required_capabilities=["base financeira normalizada", "estrutura DRE"],
        optional_capabilities=["resultado DRE persistido"],
        allowed_tools=[
            "ton_get_dre_readiness",
            "ton_get_dre_result",
            "ton_get_billing_summary",
            "ton_get_budget_summary",
            "ton_get_reconciliation_summary",
        ],
    ),
    SpecialistDefinition(
        key="AUDITOR",
        name="TON AUDITOR",
        objective="Verificar revisão da base e rastrear evidências.",
        domain="AUDIT",
        required_capabilities=["revisão financeira"],
        allowed_tools=[
            "ton_list_sources",
            "ton_get_source_status",
            "ton_get_financial_review_summary",
            "ton_list_findings",
            "ton_get_finding",
        ],
    ),
    SpecialistDefinition(
        key="CEO",
        name="TON CEO",
        objective="Resumir os resultados dos especialistas para decisão.",
        domain="AUDIT",
        required_capabilities=["resultado CFO ou AUDITOR"],
        allowed_tools=["ton_generate_executive_brief"],
    ),
    SpecialistDefinition(
        key="COO",
        name="TON COO",
        objective="Analisar produção e produtividade.",
        domain="OPERATIONAL",
        required_capabilities=["produção integrada e regras aprovadas"],
        allowed_tools=[],
    ),
    SpecialistDefinition(
        key="FLEET",
        name="TON FROTA",
        objective="Analisar frota e abastecimento.",
        domain="FLEET",
        required_capabilities=["frota e abastecimento integrados"],
        allowed_tools=[],
    ),
    SpecialistDefinition(
        key="CONTRACTS",
        name="TON CONTRATOS",
        objective="Analisar obrigações e vigência contratual.",
        domain="CONTRACT",
        required_capabilities=["cadastro mestre contratual e regras aprovadas"],
        allowed_tools=[],
    ),
    SpecialistDefinition(
        key="COMPLIANCE",
        name="TON COMPLIANCE",
        objective="Identificar pendências documentais para revisão humana.",
        domain="COMPLIANCE",
        required_capabilities=["documentos legais e regras aprovadas"],
        allowed_tools=[],
    ),
    SpecialistDefinition(
        key="PROCUREMENT",
        name="TON PROCUREMENT",
        objective="Analisar compras e fornecedores.",
        domain="PROCUREMENT",
        required_capabilities=["compras integradas e regras aprovadas"],
        allowed_tools=[],
    ),
    SpecialistDefinition(
        key="HR",
        name="TON RH",
        objective="Analisar custos de pessoal.",
        domain="HR",
        required_capabilities=["folha integrada e regras aprovadas"],
        allowed_tools=[],
    ),
)

ROUTINES = (
    ("R1", "Varredura diária de exceções", "Regras de exceção e limiares aprovados"),
    ("R2", "Auditoria semanal de combustível", "Frota e abastecimento integrados"),
    (
        "R3",
        "Fechamento preliminar mensal",
        "Fontes financeiras autorizadas; decisões pendentes são publicadas como bloqueios",
    ),
    (
        "R4",
        "Reconciliação contratual mensal",
        "Cadastro mestre contratual e regras aprovadas",
    ),
    ("R5", "Dinheiro Escondido", "Oportunidades e fontes de quantificação"),
    ("R6", "Pacote executivo", "Configuração de execução autônoma e destinatários"),
    (
        "R7",
        "Sentinela de vigência/reajuste contratual",
        "Contrato, vigência e índices autorizados",
    ),
    ("R8", "Sentinela de recebíveis", "Recebíveis e registros de pagamento integrados"),
    (
        "R9",
        "Verificação de ações vencidas",
        "Executor de verificação de ações e prazos",
    ),
)
