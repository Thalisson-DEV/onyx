"""FinancialReviewEngine: deterministic evaluation of one parsed import.

Input: DATA-002 records and diagnostics plus a :class:`RuleContext`.
Output: rule evaluations, detections with explanations and recommendations,
a diagnostic treatment summary and statistics. The engine is pure; persistence
belongs to :mod:`onyx.db.ton.financial_review`.
"""

from collections import Counter
from collections.abc import Iterable, Mapping

from onyx.db.ton.enums import RuleVersionOutcome
from onyx.ton.financial_review.catalog import (
    DEFAULT_CATALOG,
    RuleCatalog,
    diagnostic_policy_for,
)
from onyx.ton.financial_review.explanations import explain
from onyx.ton.financial_review.models import (
    EngineRuleStatus,
    EvaluatedDetection,
    ReviewEvaluationResult,
    ReviewRecord,
    RuleContext,
    RuleEvaluation,
)
from onyx.ton.financial_review.recommendations import build_recommendation
from onyx.ton.financial_review.rules import (
    DEFAULT_EXECUTORS,
    ReviewIndex,
    RuleExecutor,
)
from onyx.ton.ng_financial.models import (
    DiagnosticCode,
    DiagnosticLevel,
    ParseDiagnostic,
)


class RuleCatalogError(ValueError):
    """The catalog and the executor registry disagree."""


class FinancialReviewEngine:
    def __init__(
        self,
        catalog: RuleCatalog = DEFAULT_CATALOG,
        executors: Mapping[str, RuleExecutor] = DEFAULT_EXECUTORS,
    ) -> None:
        for definition in catalog:
            runnable = definition.status in (
                EngineRuleStatus.ACTIVE,
                EngineRuleStatus.EXPERIMENTAL,
            )
            if runnable and definition.executor_key not in executors:
                raise RuleCatalogError(f"No executor for {definition.executor_key}")
        self.catalog = catalog
        self.executors = executors

    def evaluate(
        self,
        records: Iterable[ReviewRecord],
        diagnostics: Iterable[ParseDiagnostic],
        context: RuleContext,
    ) -> ReviewEvaluationResult:
        index = ReviewIndex(records, diagnostics)
        evaluations: list[RuleEvaluation] = []
        detections: list[EvaluatedDetection] = []
        verification_index: dict[str, dict[str, int]] = {}
        for definition in self.catalog:
            if definition.status is EngineRuleStatus.DISABLED:
                evaluations.append(
                    RuleEvaluation(
                        rule_key=definition.key,
                        rule_version=definition.version,
                        engine_status=definition.status,
                        outcome=RuleVersionOutcome.SKIPPED_NOT_APPLICABLE,
                        detection_count=0,
                        skip_reason="DISABLED",
                    )
                )
                continue
            missing = definition.missing_sources(context.available_sources)
            if definition.status is EngineRuleStatus.BLOCKED or missing:
                evaluations.append(
                    RuleEvaluation(
                        rule_key=definition.key,
                        rule_version=definition.version,
                        engine_status=definition.status,
                        outcome=RuleVersionOutcome.SKIPPED_MISSING_DATA,
                        detection_count=0,
                        skip_reason="MISSING_SOURCES:"
                        + ",".join(item.value for item in missing),
                    )
                )
                continue
            output = self.executors[definition.executor_key](definition, index, context)
            if definition.produces_findings:
                ordered = sorted(
                    output.detections,
                    key=lambda item: (item.sheet_month or 0, item.review_key),
                )
                detections.extend(
                    EvaluatedDetection(
                        detection=item,
                        explanation=explain(item),
                        recommendation=build_recommendation(definition, item),
                    )
                    for item in ordered
                )
                verification_index[definition.key] = dict(output.verification_keys)
                count = len(ordered)
            else:
                # Experimental rules report what they saw and create nothing.
                count = 0
            evaluations.append(
                RuleEvaluation(
                    rule_key=definition.key,
                    rule_version=definition.version,
                    engine_status=definition.status,
                    outcome=RuleVersionOutcome.EXECUTED,
                    detection_count=count,
                    observations=dict(sorted(output.observations.items())),
                )
            )
        return ReviewEvaluationResult(
            evaluations=tuple(evaluations),
            detections=tuple(detections),
            diagnostic_summary=_diagnostic_summary(index.diagnostics),
            statistics={
                "records_evaluated": len(index.records),
                "diagnostics_evaluated": len(index.diagnostics),
                "diagnostics_truncated": int(
                    context.execution_statistics.get("diagnostics_total", 0)
                    > context.execution_statistics.get("diagnostics_stored", 0)
                ),
                "rules_in_catalog": len(self.catalog),
                "rules_executed": sum(
                    item.outcome is RuleVersionOutcome.EXECUTED for item in evaluations
                ),
                "rules_skipped": sum(
                    item.outcome is not RuleVersionOutcome.EXECUTED
                    for item in evaluations
                ),
                "detections": len(detections),
            },
            verification_index=verification_index,
        )


def _diagnostic_summary(
    diagnostics: Iterable[ParseDiagnostic],
) -> dict[str, dict[str, str | int]]:
    counts: Counter[tuple[DiagnosticCode, DiagnosticLevel]] = Counter(
        (item.code, item.level) for item in diagnostics
    )
    summary: dict[str, dict[str, str | int]] = {}
    for (code, level), count in sorted(
        counts.items(), key=lambda item: (item[0][0].value, item[0][1].value)
    ):
        policy = diagnostic_policy_for(code, level)
        summary[f"{code.value}:{level.value}"] = {
            "count": count,
            "treatment": policy.treatment.value,
            "rule_key": policy.rule_key or "",
        }
    return summary
