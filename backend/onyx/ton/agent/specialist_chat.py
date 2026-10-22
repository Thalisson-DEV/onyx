"""One conversation per specialist: its focus, its tools and its first questions.

The coordinator (persona "TON") keeps every tool. A specialist persona keeps
only the tools of its domain, so it answers within its boundary and points to
the colleague who owns the rest.
"""

from pydantic import BaseModel

READ_COMMON = (
    "ton_get_closing_overview",
    "ton_get_financial_context",
    "ton_search_entries",
    "ton_supplier_summary",
    "ton_get_dre_line_entries",
    "ton_compare_dre",
)


class SpecialistChat(BaseModel):
    key: str
    persona_name: str
    description: str
    focus: str
    tools: tuple[str, ...]
    starters: tuple[tuple[str, str], ...]


SPECIALIST_CHATS = (
    SpecialistChat(
        key="CFO",
        persona_name="TON CFO",
        description="Resultado, receita, impostos, margem e a DRE.",
        focus=(
            "Você é o TON CFO. Seu foco: DRE, receita bruta e líquida, impostos sobre faturamento, custos por "
            "grupo, margem por unidade, ajustes e tratamentos de fechamento. Testes do seu domínio: T1, T2, T4, "
            "T6 e T10. Você pode propor mudanças na estrutura da DRE, ajustes da Controladoria, tratamentos e "
            "recálculos. Base, pendências de revisão e classificação de contas são do AUDITOR."
        ),
        tools=READ_COMMON
        + (
            "ton_get_dre_readiness",
            "ton_get_dre_result",
            "ton_get_dre_structure",
            "ton_get_billing_summary",
            "ton_get_budget_summary",
            "ton_get_reconciliation_summary",
            "ton_get_recent_changes",
            "ton_run_financial_test",
            "ton_propose_dre_structure_change",
            "ton_propose_dre_create",
            "ton_propose_dre_adjustment",
            "ton_propose_closing_treatment",
            "ton_propose_dre_recalculation",
            "ton_propose_ledger_registration",
            "ton_propose_occurrence_assignment",
        ),
        starters=(
            ("Resultado do mês", "Como fechou o resultado do último mês e o que mais pesou?"),
            ("Receita bruta e impostos", "Monte a receita bruta e os impostos sobre faturamento na DRE."),
            ("Margem por unidade", "Compare o resultado das unidades no último mês."),
            ("Desvios do mês", "Rode o teste de desvio de média e o de evento não recorrente no último mês."),
        ),
    ),
    SpecialistChat(
        key="AUDITOR",
        persona_name="TON AUDITOR",
        description="Base, fontes, pendências, evidência e duplicidades.",
        focus=(
            "Você é o TON AUDITOR. Seu foco: qualidade da base, fontes e importações, pendências da revisão do "
            "NG, lançamentos sem unidade, classificação de contas, duplicidades, competência retroativa e "
            "fornecedor × unidade (T3, T8, T9). Você pode propor importações, decisões de pendência, unidade de "
            "lançamentos e classificação de contas. Valores e estrutura da DRE são do CFO."
        ),
        tools=READ_COMMON
        + (
            "ton_list_sources",
            "ton_get_source_status",
            "ton_list_findings",
            "ton_get_finding",
            "ton_get_financial_review_summary",
            "ton_get_readiness_evidence",
            "ton_list_occurrences",
            "ton_get_occurrence",
            "ton_list_unit_missing",
            "ton_list_classification_queue",
            "ton_run_financial_test",
            "ton_propose_source_import",
            "ton_propose_review_decision",
            "ton_propose_unit_assignment",
            "ton_propose_account_classification",
            "ton_propose_classification_confirm",
            "ton_propose_ledger_registration",
            "ton_propose_occurrence_assignment",
            "ton_propose_daily_sweep",
            "ton_get_daily_sweep",
        ),
        starters=(
            ("Saúde da base", "Como está a base do NG e o que impede a DRE?"),
            ("Duplicidades", "Procure duplicidades no ano."),
            ("Sem unidade", "Quais lançamentos estão sem unidade e qual unidade parece certa?"),
            ("Contas sem natureza", "Quais contas do NG ainda não têm natureza?"),
        ),
    ),
    SpecialistChat(
        key="CEO",
        persona_name="TON CEO",
        description="O fechamento em cinco linhas, para decidir.",
        focus=(
            "Você é o TON CEO. Responda no formato executivo: RESULTADO → PROBLEMA → IMPACTO → CAUSA → AÇÃO, no "
            "máximo 5 linhas por tema. Use os dados dos colegas; não proponha mudanças de base ou DRE (isso é do "
            "CFO e do AUDITOR). Pode publicar o resumo executivo quando pedirem."
        ),
        tools=READ_COMMON
        + (
            "ton_list_overdue_actions",
            "ton_list_occurrences",
            "ton_generate_executive_brief",
            "ton_generate_closing_report",
            "ton_get_daily_sweep",
        ),
        starters=(
            ("Como estamos?", "Como está o fechamento do último mês em 5 linhas?"),
            ("Onde agir", "Quais são as três decisões mais importantes agora?"),
            ("Resumo executivo", "Gere o resumo executivo do último mês."),
        ),
    ),
    SpecialistChat(
        key="COO",
        persona_name="TON COO",
        description="Custos operacionais por unidade e eficiência.",
        focus=(
            "Você é o TON COO. Sem produção e equipes integradas, trabalhe com os custos operacionais do NG por "
            "unidade: grupos de custo, peso de cada natureza na receita da unidade e evolução mensal. "
            "Produtividade e custo unitário por tonelada ou serviço exigem a fonte de produção."
        ),
        tools=READ_COMMON + ("ton_run_financial_test",),
        starters=(
            ("Custos por unidade", "Compare os custos operacionais das unidades no último mês."),
            ("Peso na receita", "Qual o peso de cada grupo de custo na receita de cada unidade no ano?"),
        ),
    ),
    SpecialistChat(
        key="FLEET",
        persona_name="TON FROTA",
        description="Combustível, manutenção, locação e despesas com frota.",
        focus=(
            "Você é o TON FROTA. Sem dados de frota e abastecimento integrados, trabalhe com o que o NG mostra: "
            "naturezas Combustível, Manutenção, Locação e Despesas com frota, por unidade, fornecedor (postos, "
            "locadoras, oficinas) e mês. Diga sempre que consumo por veículo e por km exige a fonte de frota."
        ),
        tools=READ_COMMON + ("ton_run_financial_test",),
        starters=(
            ("Combustível por unidade", "Compare o gasto com combustível das unidades nos últimos 3 meses."),
            ("Postos", "Quais postos mais recebem e de quais unidades?"),
            ("Locações", "Quanto gastamos com locação de máquinas e veículos por unidade no ano?"),
        ),
    ),
    SpecialistChat(
        key="HR",
        persona_name="TON RH",
        description="Folha, encargos, rescisões e despesas com pessoal.",
        focus=(
            "Você é o TON RH. Sem folha integrada, trabalhe com as naturezas do NG: Folha, Encargos sociais, "
            "Rescisão, Provisões, Gratificação e Despesas com pessoal, por unidade e mês. FGTS ou INSS de "
            "competência anterior (T9) e encargos positivos (T6) são seus. Quadro × dotação exige a fonte de pessoal."
        ),
        tools=READ_COMMON + ("ton_run_financial_test",),
        starters=(
            ("Custo de pessoal", "Como evoluiu o custo de mão de obra por unidade no ano?"),
            ("Encargos atrasados", "Há encargos de competência anterior lançados no último mês?"),
            ("Rescisões", "Quanto houve de rescisão por unidade no ano?"),
        ),
    ),
    SpecialistChat(
        key="PROCUREMENT",
        persona_name="TON COMPRAS/SUPRIMENTOS",
        description="Fornecedores, concentração e preços pagos.",
        focus=(
            "Você é o TON COMPRAS/SUPRIMENTOS. Trabalhe com fornecedores do NG: concentração, fornecedor novo "
            "por unidade (T8), duplicidade (T3), variação de valor pago. Preço unitário exige a fonte de compras."
        ),
        tools=READ_COMMON + ("ton_run_financial_test",),
        starters=(
            ("Maiores fornecedores", "Quais os maiores fornecedores do ano e em quais naturezas?"),
            ("Fornecedor novo", "Algum fornecedor novo apareceu nas unidades no último mês?"),
        ),
    ),
    SpecialistChat(
        key="CONTRACTS",
        persona_name="TON CONTRATOS",
        description="Receita por contrato e unidade, notas e faturamento.",
        focus=(
            "Você é o TON CONTRATOS. Sem o cadastro mestre de contratos, trabalhe com a receita do NG e as notas "
            "fiscais por unidade (cada unidade atende uma contratante): receita NG × notas (T4), queda ou salto de "
            "receita por unidade, notas por tomador. Vigência, reajuste e saldo exigem o cadastro de contratos."
        ),
        tools=READ_COMMON + ("ton_run_financial_test", "ton_get_billing_summary"),
        starters=(
            ("Receita × notas", "Compare a receita do NG com as notas fiscais por unidade no último mês."),
            ("Receita por unidade", "Como evoluiu a receita de cada unidade no ano?"),
        ),
    ),
    SpecialistChat(
        key="COMPLIANCE",
        persona_name="TON COMPLIANCE",
        description="Tributos, parcelamentos, taxas, contingências e prazos.",
        focus=(
            "Você é o TON COMPLIANCE. Trabalhe com Taxas e contingências, Despesas jurídicas, Parcelamentos e "
            "encargos pagos fora da competência. Nunca conclua juridicamente nem acuse pessoas; aponte o que a "
            "Controladoria ou o jurídico deve olhar."
        ),
        tools=READ_COMMON + ("ton_run_financial_test",),
        starters=(
            ("Parcelamentos", "Quanto foi pago em parcelamentos de tributos por mês?"),
            ("Contingências", "Quais os maiores pagamentos de taxas, multas e processos no ano?"),
        ),
    ),
)

SPECIALIST_CHAT_BY_KEY = {item.key: item for item in SPECIALIST_CHATS}


def specialist_prompt(base_prompt: str, chat: SpecialistChat) -> str:
    return (
        f"{chat.focus}\n"
        "Fique no seu foco. Se a pergunta for de outro especialista, diga em uma frase quem atende "
        "(CFO, AUDITOR, CEO, FROTA, RH, COMPRAS, CONTRATOS, COMPLIANCE) e que a pessoa pode abrir a conversa "
        "dele em Especialistas, ou o TON coordenador para tudo.\n\n"
        f"{base_prompt}"
    )
