"""DATA-003 engine, rules, recommendations, policy and calibration.

Synthetic workbooks only. Every workbook goes through the real DATA-002 parser,
so the engine is tested on the same records production would give it.
"""

import ast
import datetime
import re
from collections.abc import Mapping, Sequence
from dataclasses import replace
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pytest
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from onyx.db.ton.enums import (
    OccurrenceStatus,
    OccurrenceVerificationResult,
    RuleVersionOutcome,
)
from onyx.db.ton.models import RuleVersion
from onyx.db.ton.rule_versions import compute_definition_hash
from onyx.ton.financial_review.adapters import review_records_from_parse
from onyx.ton.financial_review.calibration import (
    ChangeStructure,
    FieldDeltaGroup,
    calibrate,
    delta_groups,
)
from onyx.ton.financial_review.catalog import (
    DEFAULT_CATALOG,
    DIAGNOSTIC_POLICY,
    POP_CAPABILITIES,
    POP_NAMES,
    RuleCatalog,
    diagnostic_policy_for,
    rule_version_fields,
)
from onyx.ton.financial_review.dataset import (
    EventFact,
    FindingState,
    combine,
    dataset_revision,
    excluded_rows,
    finding_disposition,
    state_as_of,
)
from onyx.ton.financial_review.engine import FinancialReviewEngine, RuleCatalogError
from onyx.ton.financial_review.models import (
    DetectionScope,
    DiagnosticTreatment,
    EngineRuleStatus,
    EvaluatedDetection,
    ImpactStatus,
    RecommendationEvidenceLevel,
    RecommendationKind,
    ReviewCategory,
    ReviewDisposition,
    ReviewEvaluationResult,
    RuleContext,
    RuleEvaluation,
    SourceRequirement,
)
from onyx.ton.financial_review.rules import (
    DEFAULT_EXECUTORS,
    record_base_key,
    record_keys,
)
from onyx.ton.ng_financial.models import (
    DiagnosticCode,
    DiagnosticLevel,
    ParsedImportResult,
)
from onyx.ton.ng_financial.parser import NgFinancialExportParser

JAN_1 = datetime.date(2026, 1, 5)
JAN_2 = datetime.date(2026, 1, 6)
FEB_1 = datetime.date(2026, 2, 3)
MAR_1 = datetime.date(2026, 3, 9)
Row = list[object]


def launch(
    account: str | None = None,
    day: object = None,
    unit: str | None = "001 - Synthetic unit",
    document: str | None = "SYN-1",
    history: str = "Synthetic history",
    movement: object = 100,
    interest: object = 0,
    final: object = 100,
) -> Row:
    """One A:Q row. F movement, K interest, Q final."""
    return [
        account,
        day,
        unit,
        document,
        history,
        movement,
        0,
        movement,
        None,
        None,
        interest,
        0,
        0,
        0,
        0,
        0,
        final,
    ]


def book(sheets: Mapping[str, Sequence[Row]]) -> bytes:
    workbook = Workbook()
    workbook.remove(cast(Worksheet, workbook.active))
    for name, rows in sheets.items():
        sheet = workbook.create_sheet(name)
        for row in rows:
            sheet.append(list(row))
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def parse(content: bytes, snapshot_id: UUID | None = None) -> ParsedImportResult:
    return NgFinancialExportParser().parse(content, snapshot_id or uuid4())


def context_for(
    result: ParsedImportResult,
    *,
    execution_statistics: Mapping[str, int] | None = None,
    account_label_reference: Mapping[str, str] | None = None,
) -> RuleContext:
    rejected = sum(
        1
        for item in result.diagnostics
        if item.level is DiagnosticLevel.ERROR
        and item.code is not DiagnosticCode.FORMULA_UNSUPPORTED
    )
    statistics = execution_statistics or {
        "records_rejected": rejected,
        "diagnostics_total": len(result.diagnostics),
        "diagnostics_stored": len(result.diagnostics),
    }
    return RuleContext(
        source_id=UUID(int=7),
        snapshot_id=result.snapshot_id,
        execution_id=UUID(int=8),
        execution_status="PARTIAL" if rejected else "SUCCEEDED",
        execution_statistics=statistics,
        account_label_reference=account_label_reference,
    )


def review(
    content: bytes,
    *,
    engine: FinancialReviewEngine | None = None,
    account_label_reference: Mapping[str, str] | None = None,
) -> tuple[ParsedImportResult, ReviewEvaluationResult]:
    result = parse(content)
    evaluation = (engine or FinancialReviewEngine()).evaluate(
        review_records_from_parse(result.records),
        result.diagnostics,
        context_for(result, account_label_reference=account_label_reference),
    )
    return result, evaluation


def detections(
    evaluation: ReviewEvaluationResult, rule_key: str
) -> list[EvaluatedDetection]:
    return [
        item for item in evaluation.detections if item.detection.rule_key == rule_key
    ]


def evaluation_for(evaluation: ReviewEvaluationResult, rule_key: str) -> RuleEvaluation:
    return next(item for item in evaluation.evaluations if item.rule_key == rule_key)


CLEAN = {
    "Jan": [
        launch("1.1 - Synthetic account", JAN_1, document="SYN-1"),
        launch(None, JAN_2, document="SYN-2", movement=50, final=50),
    ]
}


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


class TestCleanInput:
    def test_clean_records_produce_no_detection(self) -> None:
        _, evaluation = review(book(CLEAN))
        assert evaluation.detections == ()
        assert evaluation.statistics["records_evaluated"] == 2

    def test_every_catalog_rule_is_accounted_for(self) -> None:
        _, evaluation = review(book(CLEAN))
        assert {item.rule_key for item in evaluation.evaluations} == set(
            DEFAULT_CATALOG.keys()
        )
        for item in evaluation.evaluations:
            definition = DEFAULT_CATALOG.get(item.rule_key)
            if definition.status is EngineRuleStatus.BLOCKED:
                assert item.outcome is RuleVersionOutcome.SKIPPED_MISSING_DATA
                assert item.skip_reason and item.skip_reason.startswith(
                    "MISSING_SOURCES:"
                )
            else:
                assert item.outcome is RuleVersionOutcome.EXECUTED


class TestUnitMissing:
    def workbook(self) -> bytes:
        return book(
            {
                "Jan": [
                    launch("1.1 - Synthetic account", JAN_1, unit=None, final=77),
                    launch(None, JAN_2, document="SYN-2"),
                ]
            }
        )

    def test_positive(self) -> None:
        result, evaluation = review(self.workbook())
        [item] = detections(evaluation, "NGF-UNIT-MISSING")
        detection = item.detection
        assert detection.scope is DetectionScope.RECORD
        assert detection.facts["row_number"] == 1
        assert detection.record_ids == (
            review_records_from_parse(result.records)[0].id,
        )
        assert detection.impact.status is ImpactStatus.EXACT
        assert detection.impact.amount == Decimal("77")
        assert "unidade administrativa" in item.explanation
        recommendation = item.recommendation
        assert recommendation.kind is RecommendationKind.SOURCE_CORRECTION_REQUIRED
        assert recommendation.suggested_value is None
        assert recommendation.target_field == "administrative_unit"

    def test_negative(self) -> None:
        _, evaluation = review(book(CLEAN))
        assert detections(evaluation, "NGF-UNIT-MISSING") == []

    def test_whitespace_unit_counts_as_missing(self) -> None:
        _, evaluation = review(
            book({"Jan": [launch("1.1 - Synthetic account", JAN_1, unit="   ")]})
        )
        assert len(detections(evaluation, "NGF-UNIT-MISSING")) == 1

    def test_new_date_with_blank_unit_does_not_inherit_the_previous_unit(
        self,
    ) -> None:
        _, evaluation = review(
            book(
                {
                    "Jan": [
                        launch("1.1 - Synthetic account", JAN_1),
                        launch(None, JAN_2, unit=None, document="SYN-2"),
                    ]
                }
            )
        )
        [item] = detections(evaluation, "NGF-UNIT-MISSING")
        assert item.detection.facts["row_number"] == 2

    def test_missing_final_amount_leaves_impact_unknown(self) -> None:
        _, evaluation = review(
            book(
                {
                    "Jan": [
                        launch("1.1 - Synthetic account", JAN_1, unit=None, final=None)
                    ]
                }
            )
        )
        [item] = detections(evaluation, "NGF-UNIT-MISSING")
        assert item.detection.impact.status is ImpactStatus.UNKNOWN

    def test_identity_excludes_the_corrected_unit(self) -> None:
        original = parse(self.workbook())
        corrected = parse(
            book(
                {
                    "Jan": [
                        launch("1.1 - Synthetic account", JAN_1, final=77),
                        launch(None, JAN_2, document="SYN-2"),
                    ]
                }
            )
        )
        excluded = frozenset({"administrative_unit"})
        before = review_records_from_parse(original.records)[0]
        after = review_records_from_parse(corrected.records)[0]
        assert record_base_key(before, excluded) == record_base_key(after, excluded)
        assert record_base_key(before, frozenset()) != record_base_key(
            after, frozenset()
        )

    def test_identity_is_stable_across_reparse(self) -> None:
        content = self.workbook()
        first = review_records_from_parse(parse(content).records)
        second = review_records_from_parse(parse(content).records)
        assert {item.id for item in first}.isdisjoint({item.id for item in second})
        excluded = frozenset({"administrative_unit"})
        assert [key.review_key for key in record_keys(first, excluded).values()] == [
            key.review_key for key in record_keys(second, excluded).values()
        ]


class TestRejectedRows:
    def workbook(self) -> bytes:
        return book(
            {
                "Jan": [
                    launch("1.1 - Synthetic account", JAN_1),
                    launch(None, JAN_2, document="SYN-2", interest="not a number"),
                ]
            }
        )

    def test_rejected_row_becomes_a_diagnostic_finding(self) -> None:
        result, evaluation = review(self.workbook())
        assert len(result.records) == 1
        [item] = detections(evaluation, "NGF-SRC-ROW-REJECTED")
        detection = item.detection
        assert detection.scope is DetectionScope.DIAGNOSTIC
        assert detection.record_ids == ()
        assert detection.facts["diagnostic_code"] == "INVALID_AMOUNT"
        assert detection.facts["column"] == "K"
        assert detection.facts["row_number"] == 2
        assert detection.impact.status is ImpactStatus.UNKNOWN
        assert item.recommendation.kind is RecommendationKind.SOURCE_CORRECTION_REQUIRED
        assert item.recommendation.target_field == "interest_amount"
        assert item.recommendation.suggested_value is None

    def test_unlocated_rejections_beyond_the_diagnostic_cap_are_a_blind_spot(
        self,
    ) -> None:
        result = parse(self.workbook())
        statistics = {
            "records_rejected": 3,
            "diagnostics_total": 5000,
            "diagnostics_stored": 2000,
        }
        evaluation = FinancialReviewEngine().evaluate(
            review_records_from_parse(result.records),
            result.diagnostics,
            context_for(result, execution_statistics=statistics),
        )
        scopes = [
            item.detection.scope
            for item in detections(evaluation, "NGF-SRC-ROW-REJECTED")
        ]
        assert scopes.count(DetectionScope.EXECUTION) == 1
        assert evaluation.statistics["diagnostics_truncated"] == 1

    def test_no_rejection_no_finding(self) -> None:
        _, evaluation = review(book(CLEAN))
        assert detections(evaluation, "NGF-SRC-ROW-REJECTED") == []


class TestDuplicates:
    def test_exact_duplicates_are_candidates_and_all_are_kept(self) -> None:
        row = launch("1.1 - Synthetic account", JAN_1)
        result, evaluation = review(
            book({"Jan": [row, launch(None, None), launch(None, JAN_2, document="X")]})
        )
        assert len(result.records) == 3
        [item] = detections(evaluation, "NGF-DUP-EXACT")
        assert item.detection.scope is DetectionScope.RECORD_GROUP
        assert len(item.detection.record_ids) == 2
        assert item.detection.impact.status is ImpactStatus.CONDITIONAL
        assert item.detection.impact.amount == Decimal("100")
        assert item.recommendation.kind is RecommendationKind.REQUEST_JUSTIFICATION
        assert (
            item.recommendation.evidence_level is RecommendationEvidenceLevel.AMBIGUOUS
        )

    def test_same_amount_alone_is_not_a_duplicate(self) -> None:
        _, evaluation = review(
            book(
                {
                    "Jan": [
                        launch("1.1 - Synthetic account", JAN_1, history="A"),
                        launch(None, None, history="B"),
                    ]
                }
            )
        )
        assert detections(evaluation, "NGF-DUP-EXACT") == []
        observations = evaluation_for(evaluation, "NGF-DUP-NEAR").observations
        assert observations["near_duplicate_groups"] == 1

    def test_duplicates_in_different_months_are_not_flagged(self) -> None:
        row = launch("1.1 - Synthetic account", JAN_1)
        _, evaluation = review(book({"Jan": [row], "Fev": [row]}))
        assert detections(evaluation, "NGF-DUP-EXACT") == []

    def test_year_prefixed_document_copy_is_flagged_and_first_is_kept(self) -> None:
        prefixed = f"{JAN_1.year % 100:02d}" + "123".zfill(11)
        _, evaluation = review(
            book(
                {
                    "Jan": [
                        launch("1.1 - Synthetic account", JAN_1, document="123"),
                        launch(None, None, document=prefixed, history="Other"),
                        launch(None, JAN_2, document="124"),
                    ]
                }
            )
        )
        [item] = detections(evaluation, "NGF-DUP-DOC")
        assert len(item.detection.record_ids) == 1
        assert item.detection.facts["row_number"] == 2
        assert item.detection.facts["kept_row_number"] == 1
        assert item.detection.facts["kept_document_number"] == "123"

    def test_plain_repetition_is_not_a_document_format_duplicate(self) -> None:
        row = launch("1.1 - Synthetic account", JAN_1, document="123")
        _, evaluation = review(book({"Jan": [row, launch(None, None, document="123")]}))
        assert detections(evaluation, "NGF-DUP-DOC") == []


class TestLabelConsistency:
    def drift(self) -> bytes:
        return book(
            {
                "Jan": [launch("1.1 - Label one", JAN_1)],
                "Fev": [launch("1.1 - Label two", FEB_1)],
            }
        )

    def test_stable_classification_is_silent(self) -> None:
        _, evaluation = review(
            book(
                {
                    "Jan": [launch("1.1 - Label one", JAN_1)],
                    "Fev": [launch("1.1 - Label one", FEB_1)],
                }
            )
        )
        assert detections(evaluation, "NGF-ACCT-LABEL-DRIFT") == []

    def test_unusual_mapping_is_ambiguous_without_authority(self) -> None:
        _, evaluation = review(self.drift())
        [item] = detections(evaluation, "NGF-ACCT-LABEL-DRIFT")
        assert item.detection.facts["label_count"] == 2
        recommendation = item.recommendation
        assert recommendation.kind is RecommendationKind.REVIEW_CLASSIFICATION
        assert recommendation.evidence_level is RecommendationEvidenceLevel.AMBIGUOUS
        assert recommendation.suggested_value is None
        assert recommendation.candidate_count == 2

    def test_authoritative_mapping_gives_a_deterministic_recommendation(
        self,
    ) -> None:
        _, evaluation = review(
            self.drift(), account_label_reference={"1.1": "Label one"}
        )
        [item] = detections(evaluation, "NGF-ACCT-LABEL-DRIFT")
        recommendation = item.recommendation
        assert recommendation.kind is RecommendationKind.DETERMINISTIC_CORRECTION
        assert (
            recommendation.evidence_level is RecommendationEvidenceLevel.DETERMINISTIC
        )
        assert recommendation.suggested_value == "Label one"

    def test_unit_label_drift(self) -> None:
        _, evaluation = review(
            book(
                {
                    "Jan": [
                        launch("1.1 - Account", JAN_1, unit="007 - Name A"),
                        launch(None, JAN_2, unit="007 - Name B", document="SYN-2"),
                    ]
                }
            )
        )
        [item] = detections(evaluation, "NGF-UNIT-LABEL-DRIFT")
        assert item.detection.facts["unit_code"] == "007"
        assert item.recommendation.kind is RecommendationKind.REQUEST_INFORMATION
        assert item.recommendation.suggested_value is None


class TestMultipleFindingsOnOneRecord:
    def test_blank_unit_duplicate_carries_both_findings(self) -> None:
        row = launch("1.1 - Synthetic account", JAN_1, unit=None)
        _, evaluation = review(book({"Jan": [row, launch(None, None, unit=None)]}))
        assert len(detections(evaluation, "NGF-UNIT-MISSING")) == 2
        assert len(detections(evaluation, "NGF-DUP-EXACT")) == 1
        keys = {item.detection.review_key for item in evaluation.detections}
        assert len(keys) == len(evaluation.detections)


# ---------------------------------------------------------------------------
# Diagnostics and experimental rules
# ---------------------------------------------------------------------------


class TestDiagnosticPromotion:
    def test_every_diagnostic_code_has_a_policy(self) -> None:
        for code in DiagnosticCode:
            for level in DiagnosticLevel:
                assert diagnostic_policy_for(code, level) is not None

    def test_promotion_is_selective(self) -> None:
        assert (
            diagnostic_policy_for(
                DiagnosticCode.INVALID_AMOUNT, DiagnosticLevel.ERROR
            ).treatment
            is DiagnosticTreatment.FINDING_ELIGIBLE
        )
        assert (
            diagnostic_policy_for(
                DiagnosticCode.CELL_OUTSIDE_CONTRACT, DiagnosticLevel.INFO
            ).treatment
            is DiagnosticTreatment.TECHNICAL_ONLY
        )
        assert (
            diagnostic_policy_for(
                DiagnosticCode.SHEET_OUT_OF_SCOPE, DiagnosticLevel.INFO
            ).treatment
            is DiagnosticTreatment.TECHNICAL_ONLY
        )
        assert (
            diagnostic_policy_for(
                DiagnosticCode.FORMULA_UNSUPPORTED, DiagnosticLevel.WARNING
            ).treatment
            is DiagnosticTreatment.TECHNICAL_ONLY
        )

    def test_hierarchy_mismatch_is_never_promoted(self) -> None:
        for code in (
            DiagnosticCode.PARENT_ROW_WITHOUT_CHILD_MATCH,
            DiagnosticCode.CHILD_ROW_WITHOUT_PARENT_MATCH,
        ):
            assert (
                diagnostic_policy_for(code, DiagnosticLevel.WARNING).treatment
                is DiagnosticTreatment.EXPERIMENTAL
            )
        assert (
            DEFAULT_CATALOG.get("NGF-HIER-RECONCILIATION").status
            is EngineRuleStatus.EXPERIMENTAL
        )

    def test_hierarchy_differences_are_observed_not_found(self) -> None:
        child = launch(None, JAN_1)
        workbook = book(
            {
                "Jan": [
                    ["1 - Parent", *child[1:]],
                    launch(None, JAN_2, document="ONLY-PARENT", movement=5, final=5),
                    ["1.1 - Child", *child[1:]],
                    launch(None, JAN_2, document="ONLY-CHILD", movement=9, final=9),
                ],
                "Payroll": [["not a financial sheet"]],
            }
        )
        result, evaluation = review(workbook)
        codes = {item.code for item in result.diagnostics}
        assert DiagnosticCode.PARENT_ROW_WITHOUT_CHILD_MATCH in codes
        assert DiagnosticCode.CHILD_ROW_WITHOUT_PARENT_MATCH in codes
        assert all(
            item.detection.rule_key != "NGF-HIER-RECONCILIATION"
            for item in evaluation.detections
        )
        observed = evaluation_for(evaluation, "NGF-HIER-RECONCILIATION")
        assert observed.detection_count == 0
        assert observed.observations["parent_rows_without_child_match"] == 1
        assert observed.observations["child_rows_without_parent_match"] == 1
        summary = evaluation.diagnostic_summary
        assert summary["PARENT_ROW_WITHOUT_CHILD_MATCH:WARNING"]["treatment"] == (
            "EXPERIMENTAL"
        )
        assert summary["SHEET_OUT_OF_SCOPE:INFO"]["treatment"] == "TECHNICAL_ONLY"

    def test_competence_signal_is_diagnostic_only(self) -> None:
        _, evaluation = review(
            book(
                {
                    "Jan": [
                        launch("1.1 - Account", JAN_1),
                        launch(None, MAR_1, document="SYN-2"),
                    ]
                }
            )
        )
        observed = evaluation_for(evaluation, "NGF-DATE-EMISSION-AFTER-SHEET")
        assert observed.observations["emission_after_sheet_month"] == 1
        assert observed.detection_count == 0

    def test_final_absent_and_document_missing_are_counted(self) -> None:
        _, evaluation = review(
            book(
                {
                    "Jan": [
                        launch("1.1 - Account", JAN_1, final=0),
                        launch(None, JAN_2, document=None, final=None),
                    ]
                }
            )
        )
        final = evaluation_for(evaluation, "NGF-AMT-FINAL-ABSENT").observations
        assert final == {
            "final_absent_with_movement": 1,
            "final_zero_with_movement": 1,
        }
        document = evaluation_for(evaluation, "NGF-DOC-MISSING").observations
        assert document["records_without_document"] == 1


class TestRuleGating:
    def test_disabled_and_missing_source_rules_are_skipped(self) -> None:
        unit = DEFAULT_CATALOG.get("NGF-UNIT-MISSING")
        duplicate = DEFAULT_CATALOG.get("NGF-DUP-EXACT")
        catalog = DEFAULT_CATALOG.replace(
            replace(unit, status=EngineRuleStatus.DISABLED)
        ).replace(
            replace(
                duplicate,
                required_sources=(
                    SourceRequirement.NG_FINANCIAL_EXPORT,
                    SourceRequirement.BANK_STATEMENT,
                ),
            )
        )
        row = launch("1.1 - Account", JAN_1, unit=None)
        _, evaluation = review(
            book({"Jan": [row, launch(None, None, unit=None)]}),
            engine=FinancialReviewEngine(catalog),
        )
        assert evaluation.detections == ()
        assert (
            evaluation_for(evaluation, "NGF-UNIT-MISSING").outcome
            is RuleVersionOutcome.SKIPPED_NOT_APPLICABLE
        )
        assert (
            evaluation_for(evaluation, "NGF-DUP-EXACT").outcome
            is RuleVersionOutcome.SKIPPED_MISSING_DATA
        )

    def test_a_runnable_rule_needs_an_executor(self) -> None:
        unit = DEFAULT_CATALOG.get("NGF-UNIT-MISSING")
        with pytest.raises(RuleCatalogError):
            FinancialReviewEngine(DEFAULT_CATALOG.replace(replace(unit, version=2)))
        engine = FinancialReviewEngine(
            DEFAULT_CATALOG.replace(replace(unit, version=2)),
            {
                **DEFAULT_EXECUTORS,
                "NGF-UNIT-MISSING.v2": DEFAULT_EXECUTORS["NGF-UNIT-MISSING.v1"],
            },
        )
        _, evaluation = review(
            book({"Jan": [launch("1.1 - Account", JAN_1, unit=None)]}), engine=engine
        )
        [item] = detections(evaluation, "NGF-UNIT-MISSING")
        assert item.detection.rule_version == 2


class TestDeterminism:
    def test_same_input_same_output(self) -> None:
        content = book(
            {
                "Jan": [
                    launch("1.1 - Account", JAN_1, unit=None),
                    launch(None, None, unit=None),
                    launch(None, JAN_2, interest="bad"),
                ],
                "Fev": [launch("1.1 - Other label", FEB_1)],
            }
        )
        snapshot = uuid4()
        first = parse(content, snapshot)
        second = parse(content, snapshot)
        engine = FinancialReviewEngine()
        left = engine.evaluate(
            review_records_from_parse(first.records),
            first.diagnostics,
            context_for(first),
        )
        right = engine.evaluate(
            review_records_from_parse(second.records),
            second.diagnostics,
            context_for(second),
        )
        assert left == right

    def test_rules_never_suggest_a_value_without_a_deterministic_kind(self) -> None:
        _, evaluation = review(
            book(
                {
                    "Jan": [
                        launch("1.1 - Label one", JAN_1, unit=None),
                        launch(None, None, unit=None),
                        launch(None, JAN_2, interest="bad"),
                    ],
                    "Fev": [launch("1.1 - Label two", FEB_1, unit="7 - A")],
                }
            )
        )
        assert evaluation.detections
        for item in evaluation.detections:
            recommendation = item.recommendation
            assert (recommendation.suggested_value is not None) == (
                recommendation.kind is RecommendationKind.DETERMINISTIC_CORRECTION
            )


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


class TestCatalog:
    def test_pop_matrix_classifies_every_category_once(self) -> None:
        categories = [item.category for item in POP_CAPABILITIES]
        assert sorted(categories) == sorted(POP_NAMES)
        assert len(categories) == 14

    def test_runnable_rules_have_executors_and_blocked_rules_have_a_gap(
        self,
    ) -> None:
        available = frozenset({SourceRequirement.NG_FINANCIAL_EXPORT})
        for definition in DEFAULT_CATALOG:
            assert definition.version >= 1
            if definition.status in (
                EngineRuleStatus.ACTIVE,
                EngineRuleStatus.EXPERIMENTAL,
            ):
                assert definition.executor_key in DEFAULT_EXECUTORS
            if definition.status is EngineRuleStatus.BLOCKED:
                assert definition.missing_sources(available)
                assert definition.known_limitations

    def test_only_deterministic_findings_are_active(self) -> None:
        active = [
            item for item in DEFAULT_CATALOG if item.status is EngineRuleStatus.ACTIVE
        ]
        assert {item.key for item in active} == {
            "NGF-SRC-ROW-REJECTED",
            "NGF-UNIT-MISSING",
            "NGF-DUP-EXACT",
            "NGF-DUP-DOC",
            "NGF-ACCT-LABEL-DRIFT",
            "NGF-UNIT-LABEL-DRIFT",
        }
        assert all(item.rule_type.value == "DETERMINISTIC" for item in active)
        dotacao = DEFAULT_CATALOG.get("NGF-XS-DOTACAO-OVERRUN")
        assert SourceRequirement.DOTACAO in dotacao.required_sources
        assert dotacao.status is EngineRuleStatus.BLOCKED
        outlier = DEFAULT_CATALOG.get("NGF-HIST-ATYPICAL-VALUE")
        assert outlier.status is EngineRuleStatus.BLOCKED
        assert outlier.category is ReviewCategory.POP_07

    def test_every_definition_hashes_canonically(self) -> None:
        for definition in DEFAULT_CATALOG:
            version = RuleVersion(rule_id=uuid4(), **rule_version_fields(definition))
            assert compute_definition_hash(version, rule_code=definition.key)

    def test_catalog_holds_one_version_per_rule(self) -> None:
        unit = DEFAULT_CATALOG.get("NGF-UNIT-MISSING")
        with pytest.raises(ValueError):
            RuleCatalog([unit, replace(unit, version=2)])

    def test_diagnostic_policy_names_existing_rules(self) -> None:
        for item in DIAGNOSTIC_POLICY:
            if item.rule_key is not None:
                assert item.rule_key in DEFAULT_CATALOG.keys()


PRODUCTION_MODULES = (
    "catalog.py",
    "engine.py",
    "rules.py",
    "recommendations.py",
    "explanations.py",
    "dataset.py",
    "service.py",
    "adapters.py",
)
PACKAGE = Path(__file__).resolve().parents[3] / "onyx" / "ton" / "financial_review"


class TestProductionBoundaries:
    def _imports(self, name: str) -> set[str]:
        tree = ast.parse((PACKAGE / name).read_text(encoding="utf-8"))
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
            elif isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
        return modules

    def test_production_never_uses_calibration_or_a_second_parser(self) -> None:
        for name in PRODUCTION_MODULES:
            imports = self._imports(name)
            assert "onyx.ton.financial_review.calibration" not in imports, name
            assert "onyx.ton.ng_financial.diff" not in imports, name
            assert not any(module.startswith("openpyxl") for module in imports), name
            assert not any("llm" in module for module in imports), name

    def test_no_client_values_are_hardcoded(self) -> None:
        """No client name, currency amount or document-like number in rules."""
        document_like = re.compile(r"\d{7,}")
        for path in PACKAGE.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert "vale norte" not in text.casefold(), path.name
            assert "R$" not in text, path.name
            assert document_like.search(text) is None, path.name


# ---------------------------------------------------------------------------
# Reviewed dataset policy
# ---------------------------------------------------------------------------


def state(
    status: OccurrenceStatus,
    *,
    blocking: bool = True,
    verification: OccurrenceVerificationResult | None = None,
    records: tuple[UUID, ...] = (UUID(int=1),),
    rule_key: str = "NGF-UNIT-MISSING",
    scope: str = "RECORD",
    month: int | None = 1,
) -> FindingState:
    return FindingState(
        finding_id=uuid4(),
        occurrence_id=uuid4(),
        rule_key=rule_key,
        blocking=blocking,
        scope=scope,
        sheet_month=month,
        record_ids=records,
        status=status,
        verification=verification,
    )


class TestDatasetPolicy:
    def test_clean_record_is_accepted(self) -> None:
        assert combine([]).disposition is ReviewDisposition.ACCEPTED

    @pytest.mark.parametrize(
        ("status", "verification", "expected"),
        [
            (OccurrenceStatus.NEW, None, ReviewDisposition.REVIEW_REQUIRED),
            (OccurrenceStatus.REOPENED, None, ReviewDisposition.REVIEW_REQUIRED),
            (OccurrenceStatus.CONFIRMED, None, ReviewDisposition.CORRECTION_REQUIRED),
            (
                OccurrenceStatus.RISK_ACCEPTED,
                None,
                ReviewDisposition.JUSTIFIED_EXCEPTION,
            ),
            (OccurrenceStatus.DISMISSED, None, ReviewDisposition.ACCEPTED),
            (
                OccurrenceStatus.RESOLVED,
                None,
                ReviewDisposition.SUPERSEDED_BY_CORRECTION,
            ),
            (
                OccurrenceStatus.NEW,
                OccurrenceVerificationResult.PASSED,
                ReviewDisposition.SUPERSEDED_BY_CORRECTION,
            ),
            (
                OccurrenceStatus.NEW,
                OccurrenceVerificationResult.INCONCLUSIVE,
                ReviewDisposition.REVIEW_REQUIRED,
            ),
        ],
    )
    def test_blocking_finding_dispositions(
        self,
        status: OccurrenceStatus,
        verification: OccurrenceVerificationResult | None,
        expected: ReviewDisposition,
    ) -> None:
        assert finding_disposition(state(status, verification=verification)) is expected

    def test_non_blocking_finding_keeps_the_record_accepted(self) -> None:
        result = combine([state(OccurrenceStatus.NEW, blocking=False)])
        assert result.disposition is ReviewDisposition.ACCEPTED
        assert result.downstream_safe
        assert result.open_non_blocking == 1

    def test_worst_state_wins(self) -> None:
        result = combine(
            [
                state(OccurrenceStatus.RISK_ACCEPTED),
                state(OccurrenceStatus.NEW, rule_key="NGF-DUP-EXACT"),
            ]
        )
        assert result.disposition is ReviewDisposition.REVIEW_REQUIRED
        assert result.rule_keys == ("NGF-DUP-EXACT", "NGF-UNIT-MISSING")
        assert not result.downstream_safe

    def test_rejected_rows_are_excluded_until_resolved(self) -> None:
        rows = excluded_rows(
            [
                state(OccurrenceStatus.NEW, records=(), scope="DIAGNOSTIC"),
                state(OccurrenceStatus.RISK_ACCEPTED, records=(), scope="DIAGNOSTIC"),
            ]
        )
        assert [item.disposition for item in rows] == [
            ReviewDisposition.EXCLUDED_SOURCE_ERROR,
            ReviewDisposition.JUSTIFIED_EXCEPTION,
        ]

    def test_state_as_of_replays_history(self) -> None:
        occurrence = uuid4()
        start = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
        events = [
            EventFact(occurrence, 1, "DETECT", OccurrenceStatus.NEW, start, None),
            EventFact(
                occurrence,
                2,
                "ACCEPT_RISK",
                OccurrenceStatus.RISK_ACCEPTED,
                start + datetime.timedelta(days=2),
                None,
            ),
        ]
        before = state_as_of(events, start + datetime.timedelta(days=1))
        after = state_as_of(events, start + datetime.timedelta(days=3))
        assert before == (OccurrenceStatus.NEW, None, 1)
        assert after == (OccurrenceStatus.RISK_ACCEPTED, None, 2)

    def test_dataset_revision_depends_only_on_run_and_history(self) -> None:
        run = uuid4()
        occurrence = uuid4()
        first = dataset_revision(review_run_id=run, event_watermark={occurrence: 1})
        again = dataset_revision(review_run_id=run, event_watermark={occurrence: 1})
        later = dataset_revision(review_run_id=run, event_watermark={occurrence: 2})
        assert first == again != later


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------


class TestCalibration:
    def test_field_groups(self) -> None:
        assert delta_groups(("interest_amount", "final_amount")) == (
            FieldDeltaGroup.INTEREST,
            FieldDeltaGroup.FINAL_AMOUNT,
        )
        assert delta_groups(("source_extras",)) == (FieldDeltaGroup.OTHER,)

    def test_april_structure_added_row_shifts_the_next_effective_date(self) -> None:
        """Synthetic equivalent: a dated row inserted above a blank-date row."""
        original_rows = [
            launch("1.1 - Account", JAN_1, document="SYN-1"),
            launch(None, None, document="SYN-2", movement=30, final=30),
        ]
        reviewed_rows = [
            original_rows[0],
            launch(None, JAN_2, document="SYN-NEW", movement=12, final=12),
            original_rows[1],
        ]
        original = parse(book({"Abr": original_rows}))
        reviewed = parse(book({"Abr ok": reviewed_rows}))
        evaluation = FinancialReviewEngine().evaluate(
            review_records_from_parse(original.records),
            original.diagnostics,
            context_for(original),
        )
        assert evaluation.detections == ()
        report = calibrate(original, reviewed, ton_flags={})
        [month] = report.months
        assert (month.unchanged, month.changed, month.added) == (1, 1, 1)
        assert report.changed_by_signature == {"DATE": 1}
        assert report.changed_by_structure == {
            ChangeStructure.CARRY_FORWARD_AFTER_ADDED_RECORD.value: 1
        }
        assert report.added_linked_to_carry_forward == 1
        assert report.deltas_with_ton_finding == 0
        assert report.unexplained_by_signature == {"ADDED": 1, "DATE": 1}

    def test_june_structure_groups_and_ton_intersection(self) -> None:
        base = [
            launch("1.1 - Account", JAN_1, document="J-1"),
            launch(None, None, document="J-2", history="h2"),
            launch(None, None, document="J-3", unit=None),
            launch(None, JAN_2, document="J-4", unit=None, history="h4"),
            launch(None, None, document="J-5", history="h5"),
        ]
        changed = [
            launch("1.1 - Account", JAN_1, document="J-1", interest=3, final=103),
            launch(None, None, document="J-2", history="h2 edited"),
            base[2],
            base[3],
            launch(None, None, document="J-5", history="h5"),
        ]
        original = parse(book({"Jun": base}))
        reviewed = parse(book({"Jun ok": changed}))
        records = review_records_from_parse(original.records)
        evaluation = FinancialReviewEngine().evaluate(
            records, original.diagnostics, context_for(original)
        )
        by_id = {item.id: (item.sheet_month, item.row_number) for item in records}
        flags: dict[tuple[int, int], set[str]] = {}
        for item in evaluation.detections:
            for record_id in item.detection.record_ids:
                flags.setdefault(by_id[record_id], set()).add(item.detection.rule_key)
        report = calibrate(original, reviewed, ton_flags=flags)
        assert report.changed_by_signature == {
            "HISTORY": 1,
            "INTEREST+FINAL_AMOUNT": 1,
        }
        assert report.deltas_with_ton_finding == 0
        # Row 3 continues the unit of its date group; row 4 starts a new date
        # with a blank unit. The reviewer left that record unchanged.
        assert report.ton_flagged_original_records == 1
        assert report.ton_only_candidates == 1

    def test_reviewed_unit_fix_is_explained_by_a_ton_finding(self) -> None:
        original = parse(book({"Jun": [launch("1.1 - Account", JAN_1, unit=None)]}))
        reviewed = parse(book({"Jun ok": [launch("1.1 - Account", JAN_1)]}))
        report = calibrate(original, reviewed, ton_flags={(6, 1): {"NGF-UNIT-MISSING"}})
        assert report.changed_by_signature == {"UNIT": 1}
        assert report.deltas_with_ton_finding == 1
        assert report.ton_rules_on_deltas == {"NGF-UNIT-MISSING": 1}
        assert report.ton_only_candidates == 0
