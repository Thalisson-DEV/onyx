"""Pure rules of the account classification table.

Nothing here touches the database: origin inference for mappings written before
the review table existed, the prefix patterns observed in the Controladoria's
confirmed codes, and the prompt/parse pair of the AI pre-classification. A
suggestion is only ever advice; applying it is a human decision elsewhere.
"""

import json
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from onyx.ton.account_classification.models import (
    ClassificationOrigin,
    ClassificationStatus,
    PrefixPattern,
    SuggestionConfidence,
)

# Phrases the real-data setup wrote on mapping revisions. The analogy marker
# must be tested first: both phrases mention the workbook.
ANALOGY_MARKER = "ausente do BANCO DE DADOS"
WORKBOOK_MARKER = "BANCO DE DADOS"
SAMPLE_HISTORY_LIMIT = 4
SAMPLE_HISTORY_CHARS = 140
# Small batches run in parallel: answer length, not prompt size, sets latency.
SUGGESTION_BATCH_SIZE = 5
RATIONALE_CHARS = 900
QUESTION_CHARS = 300
BRIEFING_CHARS = 1500

CONFIDENCE_ALIASES = {
    "HIGH": SuggestionConfidence.HIGH,
    "ALTA": SuggestionConfidence.HIGH,
    "MEDIUM": SuggestionConfidence.MEDIUM,
    "MEDIA": SuggestionConfidence.MEDIUM,
    "MÉDIA": SuggestionConfidence.MEDIUM,
    "LOW": SuggestionConfidence.LOW,
    "BAIXA": SuggestionConfidence.LOW,
}


def infer_origin(reason: str | None) -> ClassificationOrigin:
    text = reason or ""
    if ANALOGY_MARKER in text:
        return ClassificationOrigin.ANALOGY
    if WORKBOOK_MARKER in text:
        return ClassificationOrigin.CONTROLLER_WORKBOOK
    return ClassificationOrigin.MANUAL


def default_status(origin: ClassificationOrigin) -> ClassificationStatus:
    if origin is ClassificationOrigin.ANALOGY:
        return ClassificationStatus.AWAITING_CONFIRMATION
    return ClassificationStatus.CONFIRMED


def code_prefixes(code: str) -> list[str]:
    """Proper prefixes from the most to the least specific: 8.4.0013 -> 8.4, 8."""
    parts = code.split(".")
    return [".".join(parts[:size]) for size in range(len(parts) - 1, 0, -1)]


def prefix_pattern(
    code: str, confirmed: Iterable[tuple[str, str]], minimum: int = 2
) -> PrefixPattern | None:
    """Dominant natureza among confirmed codes sharing the deepest prefix.

    ``confirmed`` holds (code, natureza) pairs the Controladoria owns; the code
    itself is ignored so a row never explains itself.
    """
    pairs = [(other, nature) for other, nature in confirmed if other != code]
    for prefix in code_prefixes(code):
        natures = [nature for other, nature in pairs if other.startswith(prefix + ".")]
        if len(natures) < minimum:
            continue
        nature, matches = Counter(natures).most_common(1)[0]
        return PrefixPattern(
            prefix=prefix, natureza=nature, matches=matches, total=len(natures)
        )
    return None


@dataclass(frozen=True)
class SuggestionInput:
    code: str
    description: str
    current_natureza: str | None
    entries: int
    total_amount: str
    units: Sequence[str]
    history: Sequence[str]
    pattern: PrefixPattern | None


@dataclass(frozen=True)
class ParsedSuggestion:
    code: str
    natureza: str
    confidence: SuggestionConfidence
    rationale: str
    question: str | None = None


@dataclass
class ParseOutcome:
    suggestions: list[ParsedSuggestion] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)


SYSTEM_PROMPT = """Você é o assistente de pré-classificação contábil do TON, a \
controladoria digital da Vale Norte. Sua tarefa: sugerir a NATUREZA gerencial de \
contas do sistema financeiro NG, usando somente as evidências fornecidas.

Regras:
- Responda apenas com a natureza exatamente como aparece na lista de naturezas.
- Use o padrão da Controladoria: contas já confirmadas por ela, o prefixo do código \
e os históricos dos lançamentos. Explique qual evidência pesou.
- Mútuos, repasses de terceiros, adiantamentos de caixa e outros movimentos que não \
são receita nem custo vão para MOVIMENTOS NÃO GERENCIAIS.
- Se a evidência for fraca ou contraditória, diga isso e use confiança BAIXA.
- A sugestão será revisada por uma pessoa da Controladoria; não invente fatos.
- Escreva a justificativa em português do Brasil, em até duas frases, sem jargão \
de TI.
- Escreva também a PERGUNTA: a única pergunta, em uma frase curta, que a \
controladora precisa responder para decidir esta conta. Ela deve ser respondível \
por quem conhece a empresa, sem olhar sistema. Exemplos: "O consignado é custo da \
empresa ou só repasse ao banco do desconto do empregado?"; "Salário líquido pago \
no NG entra na DRE como FOLHA?".

Responda apenas com JSON, sem texto fora dele, no formato:
{"sugestoes": [{"codigo": "...", "natureza": "...", "confianca": "ALTA|MEDIA|BAIXA", \
"justificativa": "...", "pergunta": "..."}]}"""


def build_prompt(
    targets: Sequence[SuggestionInput],
    natures: Sequence[tuple[str, str]],
    confirmed: Sequence[tuple[str, str, str]],
) -> str:
    """User prompt. ``natures`` = (natureza, grupo DRE); ``confirmed`` =
    (código, descrição, natureza) owned by the Controladoria."""
    lines = ["NATUREZAS (natureza -> grupo da DRE):"]
    lines += [f"- {nature} -> {group}" for nature, group in natures]
    lines.append("")
    lines.append(
        "CONTAS JÁ CONFIRMADAS PELA CONTROLADORIA (código | descrição | natureza):"
    )
    lines += [f"- {code} | {label} | {nature}" for code, label, nature in confirmed]
    lines.append("")
    lines.append("CONTAS PARA PRÉ-CLASSIFICAR:")
    for target in targets:
        lines.append(f"## {target.code} | {target.description}")
        lines.append(
            f"Lançamentos: {target.entries}; total (R$): {target.total_amount}; "
            f"unidades: {', '.join(target.units) or 'nenhuma'}"
        )
        if target.current_natureza:
            lines.append(
                f"Classificação atual, ainda não confirmada: {target.current_natureza}"
            )
        if target.pattern:
            lines.append(
                f"Padrão do prefixo {target.pattern.prefix}: "
                f"{target.pattern.matches} de {target.pattern.total} contas "
                f"confirmadas são {target.pattern.natureza}"
            )
        for history in target.history[:SAMPLE_HISTORY_LIMIT]:
            lines.append(f"Histórico: {history[:SAMPLE_HISTORY_CHARS]}")
        lines.append("")
    return "\n".join(lines)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _json_payload(text: str) -> object:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("No JSON object in the model response")
    return json.loads(cleaned[start : end + 1])


def parse_suggestions(
    text: str, expected_codes: Iterable[str], natures: Iterable[str]
) -> ParseOutcome:
    """Keep only well-formed answers for requested codes with a known natureza."""
    expected = set(expected_codes)
    by_name = {_normalize(nature): nature for nature in natures}
    outcome = ParseOutcome()
    try:
        payload = _json_payload(text)
    except (ValueError, json.JSONDecodeError):
        outcome.rejected = sorted(expected)
        return outcome
    items = payload.get("sugestoes") if isinstance(payload, dict) else None
    seen: set[str] = set()
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        code = str(item.get("codigo") or "").strip()
        if code not in expected or code in seen:
            continue
        nature = by_name.get(_normalize(str(item.get("natureza") or "")))
        confidence = CONFIDENCE_ALIASES.get(
            str(item.get("confianca") or "").strip().upper()
        )
        rationale = str(item.get("justificativa") or "").strip()
        question = " ".join(str(item.get("pergunta") or "").split())
        if nature is None or confidence is None or not rationale:
            continue
        seen.add(code)
        outcome.suggestions.append(
            ParsedSuggestion(
                code=code,
                natureza=nature,
                confidence=confidence,
                rationale=rationale[:RATIONALE_CHARS],
                question=question[:QUESTION_CHARS] or None,
            )
        )
    outcome.rejected = sorted(expected - seen)
    return outcome


def batches(items: Sequence[SuggestionInput]) -> list[list[SuggestionInput]]:
    return [
        list(items[start : start + SUGGESTION_BATCH_SIZE])
        for start in range(0, len(items), SUGGESTION_BATCH_SIZE)
    ]


BRIEFING_PROMPT = """Você é o assistente do TON e prepara a controladora da Vale \
Norte para revisar a classificação de contas do NG. Abaixo estão as contas que \
aguardam decisão, com a classificação atual e a sua sugestão.

Escreva um resumo em português do Brasil, em 3 a 5 frases curtas, sem jargão de TI:
- em quantas contas você concorda com a classificação atual, que podem ser \
confirmadas de uma vez;
- quais precisam de atenção, agrupadas por tema (ex.: descontos do empregado \
repassados a terceiros), com a pergunta de negócio que decide cada tema;
- o que muda na DRE se as sugestões forem aceitas, sem inventar valores além dos \
fornecidos.

Responda apenas com JSON: {"resumo": "..."}"""


@dataclass(frozen=True)
class BriefingItem:
    code: str
    description: str
    current: str | None
    current_group: str | None
    suggested: str
    suggested_group: str
    confidence: SuggestionConfidence
    total_amount: str
    question: str | None


def build_briefing_prompt(items: Sequence[BriefingItem]) -> str:
    lines = ["CONTAS (código | descrição | atual -> sugerida | confiança | total R$):"]
    for item in items:
        agrees = item.current == item.suggested
        lines.append(
            f"- {item.code} | {item.description} | "
            f"{item.current or 'sem natureza'} ({item.current_group or '-'}) -> "
            f"{item.suggested} ({item.suggested_group}) | {item.confidence.value} | "
            f"{item.total_amount} | {'concorda' if agrees else 'diverge'}"
        )
        if item.question and not agrees:
            lines.append(f"  pergunta: {item.question}")
    return "\n".join(lines)


def parse_briefing(text: str) -> str | None:
    try:
        payload = _json_payload(text)
    except (ValueError, json.JSONDecodeError):
        return None
    summary = payload.get("resumo") if isinstance(payload, dict) else None
    if not isinstance(summary, str) or not summary.strip():
        return None
    return summary.strip()[:BRIEFING_CHARS]
