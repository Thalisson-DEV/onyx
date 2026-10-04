"""AI pre-classification: one LLM call per batch of NG account codes.

The answer is parsed defensively and only becomes a stored suggestion; the
classification itself changes only through a human confirmation.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from onyx.llm.factory import get_default_llm
from onyx.llm.interfaces import LLM
from onyx.llm.models import SystemMessage, UserMessage
from onyx.llm.utils import llm_response_to_string
from onyx.ton.account_classification.logic import (
    SYSTEM_PROMPT,
    ParsedSuggestion,
    SuggestionInput,
    batches,
    build_prompt,
    parse_suggestions,
)
from onyx.utils.logger import setup_logger
from onyx.utils.threadpool_concurrency import run_functions_tuples_in_parallel

logger = setup_logger()

LLM_TIMEOUT_SECONDS = 180


@dataclass
class SuggestionBatchResult:
    suggestions: list[ParsedSuggestion] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    model_name: str | None = None


def _run_batch(
    llm: LLM,
    targets: list[SuggestionInput],
    natures: Sequence[tuple[str, str]],
    confirmed: Sequence[tuple[str, str, str]],
) -> tuple[list[ParsedSuggestion], list[str]]:
    codes = [item.code for item in targets]
    try:
        response = llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                UserMessage(content=build_prompt(targets, natures, confirmed)),
            ],
            timeout_override=LLM_TIMEOUT_SECONDS,
        )
        text = llm_response_to_string(response)
    except Exception:
        logger.exception("TON account pre-classification batch failed")
        return [], codes
    outcome = parse_suggestions(text, codes, [nature for nature, _ in natures])
    return outcome.suggestions, outcome.rejected


def suggest(
    targets: Sequence[SuggestionInput],
    natures: Sequence[tuple[str, str]],
    confirmed: Sequence[tuple[str, str, str]],
    llm: LLM | None = None,
) -> SuggestionBatchResult:
    result = SuggestionBatchResult()
    if not targets:
        return result
    model = llm or get_default_llm(timeout=LLM_TIMEOUT_SECONDS, temperature=0)
    result.model_name = model.config.model_name
    outputs = run_functions_tuples_in_parallel(
        [
            (_run_batch, (model, batch, natures, confirmed))
            for batch in batches(targets)
        ],
        allow_failures=True,
        max_workers=4,
    )
    for output in outputs:
        if output is None:
            continue
        suggestions, skipped = output
        result.suggestions.extend(suggestions)
        result.skipped.extend(skipped)
    covered = {item.code for item in result.suggestions} | set(result.skipped)
    result.skipped.extend(item.code for item in targets if item.code not in covered)
    return result
