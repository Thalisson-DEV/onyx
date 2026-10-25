"""Plain-language text for each review rule, as the Controladoria reads it.

The rule catalog keeps technical English descriptions for the engine; a case
sheet needs to say, in Portuguese, what the TON looked for, why it matters,
the likely cause, what to do and how the TON checks the fix.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleText:
    # "lançamento repetido" / "lançamentos repetidos"
    singular: str
    plural: str
    found: str
    matters: str
    cause: str
    action: str
    verify: str
    owner_area: str = "Financeiro"
    # How the impact is measured, in one phrase.
    impact_basis: str = "soma, em valor absoluto, dos lançamentos envolvidos"


_VERIFY_IMPORT = (
    "Na importação seguinte do NG, o TON refaz a conferência: se o problema "
    "sumir, o caso fecha como corrigido e verificado; se continuar, segue "
    "aberto e conta mais um ciclo."
)

CATALOG: dict[str, RuleText] = {
    "NGF-DUP-EXACT": RuleText(
        singular="lançamento repetido",
        plural="lançamentos repetidos",
        found=(
            "Na revisão de cada importação, o TON procura lançamentos da mesma aba "
            "com a mesma conta, data, unidade, documento, histórico e todos os "
            "valores iguais. Dois lançamentos assim quase sempre são o mesmo "
            "lançamento repetido."
        ),
        matters="Cada repetição soma o valor de novo na DRE e no caixa do mês.",
        cause="Lançamento digitado duas vezes ou bloco repetido na extração do relatório.",
        action="Excluir no NG a segunda via de cada par e importar o relatório de novo.",
        verify=_VERIFY_IMPORT,
        impact_basis="soma, em valor absoluto, da segunda via de cada par",
    ),
    "NGF-DUP-DOC": RuleText(
        singular="nota lançada duas vezes",
        plural="notas lançadas duas vezes",
        found=(
            "O TON procura lançamentos da mesma aba com a mesma conta, data e "
            "valor e o mesmo número de nota escrito de dois jeitos: curto "
            '("392") e longo ("2600000000392").'
        ),
        matters="O valor da nota entra duas vezes na DRE do mês.",
        cause="Número da nota digitado em dois formatos.",
        action="Excluir no NG o lançamento duplicado e importar o relatório de novo.",
        verify=_VERIFY_IMPORT,
        impact_basis="valor da cópia a mais",
    ),
    "NGF-DUP-NEAR": RuleText(
        singular="lançamento quase repetido",
        plural="lançamentos quase repetidos",
        found=(
            "O TON procura lançamentos da mesma aba com a mesma conta, data, "
            "documento e valores, mas histórico ou unidade diferentes."
        ),
        matters="Pode ser o mesmo pagamento lançado duas vezes com descrição diferente.",
        cause="Lançamento refeito sem excluir o anterior.",
        action="Conferir cada par no NG e excluir o que estiver repetido.",
        verify=_VERIFY_IMPORT,
    ),
    "NGF-UNIT-MISSING": RuleText(
        singular="lançamento sem unidade",
        plural="lançamentos sem unidade",
        found=(
            'O TON procura lançamentos do NG com o campo "Unidade '
            'Administrativa" vazio.'
        ),
        matters=(
            "Sem unidade, o lançamento não entra na DRE de nenhuma unidade; só o "
            "consolidado o enxerga."
        ),
        cause="O NG aceita lançamento sem unidade administrativa.",
        action=(
            "Informar no NG a unidade de cada lançamento e passar a exigir o "
            "campo no lançamento."
        ),
        verify=_VERIFY_IMPORT,
    ),
    "NGF-SRC-ROW-REJECTED": RuleText(
        singular="linha que o TON não conseguiu ler",
        plural="linhas que o TON não conseguiu ler",
        found=(
            "Na importação, o TON lê cada linha do relatório. Uma linha com data "
            "ou valor ilegível, fórmula ou formato diferente não vira lançamento "
            "e fica registrada aqui."
        ),
        matters="O valor dessas linhas fica fora da base e da DRE.",
        cause="Célula com texto, fórmula ou formato diferente no relatório exportado.",
        action="Corrigir a célula no NG ou na exportação e importar o relatório de novo.",
        verify=_VERIFY_IMPORT,
        owner_area="Controladoria",
        impact_basis="sem valor, porque a linha não pôde ser lida",
    ),
    "NGF-ACCT-LABEL-DRIFT": RuleText(
        singular="conta com duas descrições",
        plural="contas com duas descrições",
        found="O TON procura o mesmo código de conta com descrições diferentes na mesma importação.",
        matters="A mesma conta pode ser lida como duas coisas diferentes nos relatórios.",
        cause="Cadastro de conta alterado no NG sem padronizar.",
        action="Padronizar a descrição da conta no cadastro do NG.",
        verify=_VERIFY_IMPORT,
        owner_area="Contabilidade",
        impact_basis="sem valor; afeta a leitura, não o total",
    ),
    "NGF-UNIT-LABEL-DRIFT": RuleText(
        singular="unidade com duas descrições",
        plural="unidades com duas descrições",
        found="O TON procura o mesmo código de unidade escrito com nomes diferentes.",
        matters="A mesma unidade pode aparecer como duas nos relatórios.",
        cause="Cadastro de unidade alterado no NG sem padronizar.",
        action="Padronizar o nome da unidade no cadastro do NG.",
        verify=_VERIFY_IMPORT,
        owner_area="Contabilidade",
        impact_basis="sem valor; afeta a leitura, não o total",
    ),
    "NGF-AMT-COMPOSITION": RuleText(
        singular="lançamento com valores que não fecham",
        plural="lançamentos com valores que não fecham",
        found="O TON confere se movimento, retenções, líquido e valor final fecham entre si.",
        matters="Um valor final errado distorce a DRE e o caixa.",
        cause="Retenção, juros ou desconto lançados no campo errado.",
        action="Corrigir os valores do lançamento no NG.",
        verify=_VERIFY_IMPORT,
    ),
    "NGF-AMT-FINAL-ABSENT": RuleText(
        singular="lançamento sem valor final",
        plural="lançamentos sem valor final",
        found="O TON procura lançamentos com movimento e valor final zerado ou vazio.",
        matters="O lançamento existe, mas não soma na DRE.",
        cause="Baixa incompleta no NG.",
        action="Completar o valor final no NG.",
        verify=_VERIFY_IMPORT,
    ),
    "NGF-DOC-MISSING": RuleText(
        singular="lançamento sem número de documento",
        plural="lançamentos sem número de documento",
        found="O TON procura lançamentos sem número de documento.",
        matters="Sem documento, não dá para ligar o lançamento à nota nem achar duplicidade.",
        cause="Campo de documento opcional no NG.",
        action="Informar o documento no NG e passar a exigir o campo.",
        verify=_VERIFY_IMPORT,
    ),
    "NGF-DATE-EMISSION-AFTER-SHEET": RuleText(
        singular="lançamento com emissão depois do mês da aba",
        plural="lançamentos com emissão depois do mês da aba",
        found="O TON procura lançamentos cuja emissão é posterior ao mês da aba em que estão.",
        matters="Pode indicar lançamento no mês errado.",
        cause="Lançamento feito na aba de outro mês.",
        action="Conferir a data e a competência no NG.",
        verify=_VERIFY_IMPORT,
    ),
    "NGF-HIST-ATYPICAL-VALUE": RuleText(
        singular="valor fora do padrão",
        plural="valores fora do padrão",
        found="O TON compara o valor com o histórico da mesma conta e unidade.",
        matters="Valor muito acima do normal pode ser erro de digitação ou gasto a explicar.",
        cause="Erro de digitação ou gasto extraordinário.",
        action="Conferir o documento e justificar ou corrigir no NG.",
        verify=_VERIFY_IMPORT,
    ),
    "NGF-HIST-RECURRING-OMISSION": RuleText(
        singular="despesa recorrente que faltou",
        plural="despesas recorrentes que faltaram",
        found="O TON procura despesas que aparecem todo mês e faltaram neste.",
        matters="A DRE do mês fica menor do que a real.",
        cause="Lançamento esquecido ou atrasado.",
        action="Lançar a despesa no NG na competência certa.",
        verify=_VERIFY_IMPORT,
    ),
}

GENERIC = RuleText(
    singular="ocorrência",
    plural="ocorrências",
    found="O TON encontrou este caso na revisão automática dos dados importados.",
    matters="Pode distorcer a DRE ou o caixa do período.",
    cause="A confirmar com o responsável.",
    action="Conferir a origem e corrigir no sistema de onde o dado vem.",
    verify=_VERIFY_IMPORT,
    owner_area="Controladoria",
)


def text_for(rule_code: str) -> RuleText:
    return CATALOG.get(rule_code, GENERIC)


OWNER_AREAS = ("Financeiro", "Contabilidade", "Controladoria", "Unidades", "DP")
