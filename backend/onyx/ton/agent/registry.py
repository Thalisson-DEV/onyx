"""Specialist configuration, separate from current source availability."""

from onyx.ton.agent.closing_models import SpecialistDefinition

SPECIALISTS = (
    SpecialistDefinition(
        key="CFO",
        name="CFO",
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
        name="AUDITOR",
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
        name="CEO",
        objective="Resumir os resultados dos especialistas para decisão.",
        domain="AUDIT",
        required_capabilities=["resultado CFO ou AUDITOR"],
        allowed_tools=["ton_generate_executive_brief"],
    ),
    SpecialistDefinition(
        key="COO",
        name="COO",
        objective="Analisar produção e produtividade.",
        domain="OPERATIONAL",
        required_capabilities=["produção integrada e regras aprovadas"],
        allowed_tools=[],
    ),
    SpecialistDefinition(
        key="FLEET",
        name="FROTA",
        objective="Analisar frota e abastecimento.",
        domain="FLEET",
        required_capabilities=["frota e abastecimento integrados"],
        allowed_tools=[],
    ),
    SpecialistDefinition(
        key="CONTRACTS",
        name="CONTRATOS",
        objective="Analisar obrigações e vigência contratual.",
        domain="CONTRACT",
        required_capabilities=["cadastro mestre contratual e regras aprovadas"],
        allowed_tools=[],
    ),
    SpecialistDefinition(
        key="COMPLIANCE",
        name="COMPLIANCE",
        objective="Identificar pendências documentais para revisão humana.",
        domain="COMPLIANCE",
        required_capabilities=["documentos legais e regras aprovadas"],
        allowed_tools=[],
    ),
    SpecialistDefinition(
        key="PROCUREMENT",
        name="COMPRAS",
        objective="Analisar compras e fornecedores.",
        domain="PROCUREMENT",
        required_capabilities=["compras integradas e regras aprovadas"],
        allowed_tools=[],
    ),
    SpecialistDefinition(
        key="HR",
        name="RH",
        objective="Analisar custos de pessoal.",
        domain="HR",
        required_capabilities=["folha integrada e regras aprovadas"],
        allowed_tools=[],
    ),
)

ROUTINES = (
    ("R1", "Varredura de exceções", "Regras de exceção e limiares aprovados"),
    ("R2", "Auditoria de combustível", "Frota e abastecimento integrados"),
    (
        "R3",
        "Fechamento preliminar",
        "Fontes financeiras autorizadas; decisões pendentes são publicadas como bloqueios",
    ),
    ("R4", "Reconciliação contratual", "Cadastro mestre contratual e regras aprovadas"),
    ("R5", "Dinheiro Escondido", "Oportunidades e fontes de quantificação"),
    ("R6", "Pacote executivo", "Configuração de execução autônoma e destinatários"),
    ("R7", "Vigência e reajuste", "Contrato, vigência e índices autorizados"),
    ("R8", "Recebimento", "Recebíveis e registros de pagamento integrados"),
    ("R9", "Verificação de ações", "Executor de verificação de ações e prazos"),
)
