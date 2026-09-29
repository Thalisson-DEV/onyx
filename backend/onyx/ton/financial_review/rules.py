"""Rule executors. Pure functions over an indexed, immutable review input.

Each executor receives its definition, a shared :class:`ReviewIndex` and the
run context, and returns detections, diagnostic observations and the key counts
a later import needs for correction verification. No executor reads a clock,
opens a file, queries a database or sees a reviewed workbook.
"""

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from onyx.ton.financial_review.catalog import RuleDefinition
from onyx.ton.financial_review.models import (
    UNKNOWN_IMPACT,
    Detection,
    DetectionScope,
    ImpactFact,
    ImpactStatus,
    ReviewRecord,
    RuleContext,
)
from onyx.ton.ng_financial.models import (
    REJECTION_CODES,
    DiagnosticCode,
    DiagnosticLevel,
    ParseDiagnostic,
)
from onyx.ton.ng_financial.parser import AMOUNT_FIELDS, sheet_month

RECORD_KEY_SCHEME = "ngf-rk-1"
KEY_FIELDS: tuple[str, ...] = (
    "sheet_month",
    "account_code",
    "account_label",
    "emission_date",
    "administrative_unit",
    "document_number",
    "history",
    *AMOUNT_FIELDS,
)
UNIT_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)*)\s*-\s*(\S.*)$", re.S)
REJECTED_ROW_RULE = "NGF-SRC-ROW-REJECTED"


class VerificationMode:
    """How a later import can confirm that a violation disappeared."""

    RECORD = "RECORD"
    GROUP = "GROUP"
    LABEL = "LABEL"
    LOCATION = "LOCATION"


@dataclass(frozen=True)
class RuleOutput:
    detections: list[Detection] = field(default_factory=list)
    observations: dict[str, int] = field(default_factory=dict)
    # base_key -> count in this import. Empty for rules that cannot verify.
    verification_keys: dict[str, int] = field(default_factory=dict)


def _text(value: str | None) -> str | None:
    if value is None:
        return None
    normalised = unicodedata.normalize("NFC", value).strip()
    return normalised or None


def _canonical(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return "0" if value == 0 else format(value.normalize(), "f")
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, int):
        return value
    return str(value)


def _record_value(record: ReviewRecord, name: str) -> object:
    if name in record.amounts:
        return record.amounts[name]
    return {
        "sheet_month": record.sheet_month,
        "account_code": record.account_code,
        "account_label": record.account_label,
        "emission_date": record.emission_date.isoformat(),
        "administrative_unit": record.administrative_unit,
        "document_number": record.document_number,
        "history": record.history,
    }[name]


def record_base_key(record: ReviewRecord, excluded: frozenset[str]) -> str:
    """Content key without the fields a correction would change."""
    payload: list[object] = [RECORD_KEY_SCHEME]
    payload.extend(
        "*" if name in excluded else _canonical(_record_value(record, name))
        for name in KEY_FIELDS
    )
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    return f"rec:{digest}"


@dataclass(frozen=True)
class RecordKey:
    review_key: str
    base_key: str
    base_count: int


def record_keys(
    records: Sequence[ReviewRecord], excluded: frozenset[str]
) -> dict[UUID, RecordKey]:
    """Stable per-record identity. Equal content gets an ordinal in row order."""
    base_by_id = {record.id: record_base_key(record, excluded) for record in records}
    counts = Counter(base_by_id.values())
    seen: Counter[str] = Counter()
    keys: dict[UUID, RecordKey] = {}
    for record in sorted(records, key=lambda item: (item.sheet_month, item.row_number)):
        base = base_by_id[record.id]
        seen[base] += 1
        keys[record.id] = RecordKey(
            review_key=f"{base}#{seen[base]}", base_key=base, base_count=counts[base]
        )
    return keys


class ReviewIndex:
    """Grouped views built once per review. Rules share it; none mutates it."""

    def __init__(
        self,
        records: Iterable[ReviewRecord],
        diagnostics: Iterable[ParseDiagnostic],
    ) -> None:
        self.records: tuple[ReviewRecord, ...] = tuple(
            sorted(records, key=lambda item: (item.sheet_month, item.row_number))
        )
        self.diagnostics: tuple[ParseDiagnostic, ...] = tuple(diagnostics)
        self.by_id: dict[UUID, ReviewRecord] = {item.id: item for item in self.records}
        by_month: dict[int, list[ReviewRecord]] = defaultdict(list)
        by_account: dict[str, list[ReviewRecord]] = defaultdict(list)
        by_fingerprint: dict[tuple[int, str], list[ReviewRecord]] = defaultdict(list)
        for record in self.records:
            by_month[record.sheet_month].append(record)
            by_account[record.account_code].append(record)
            by_fingerprint[(record.sheet_month, record.fingerprint)].append(record)
        self.by_month = dict(by_month)
        self.by_account = dict(by_account)
        self.by_fingerprint = dict(by_fingerprint)
        by_code: dict[DiagnosticCode, list[ParseDiagnostic]] = defaultdict(list)
        for diagnostic in self.diagnostics:
            by_code[diagnostic.code].append(diagnostic)
        self.diagnostics_by_code = dict(by_code)


def _impact(amount: Decimal | None, method: str, status: ImpactStatus) -> ImpactFact:
    if amount is None:
        return UNKNOWN_IMPACT
    return ImpactFact(status=status, method=method, basis="final_amount", amount=amount)


# ---------------------------------------------------------------------------
# ACTIVE rules
# ---------------------------------------------------------------------------


def _is_rejection(diagnostic: ParseDiagnostic) -> bool:
    if diagnostic.level is not DiagnosticLevel.ERROR:
        return False
    return (
        diagnostic.code in REJECTION_CODES
        or diagnostic.code is DiagnosticCode.FORMULA_UNSUPPORTED
    )


def evaluate_rejected_rows(
    definition: RuleDefinition, index: ReviewIndex, context: RuleContext
) -> RuleOutput:
    output = RuleOutput()
    located_rejections = 0
    for diagnostic in index.diagnostics:
        if not _is_rejection(diagnostic):
            continue
        if diagnostic.code in REJECTION_CODES:
            located_rejections += 1
        month = sheet_month(diagnostic.sheet_name or "")
        key = (
            f"diag:{month or 0:02d}:{diagnostic.row_number or 0}:"
            f"{diagnostic.column or '-'}:{diagnostic.code.value}"
        )
        output.detections.append(
            Detection(
                rule_key=definition.key,
                rule_version=definition.version,
                scope=DetectionScope.DIAGNOSTIC,
                review_key=key,
                base_key=key,
                base_key_count=1,
                sheet_month=month,
                diagnostics=(diagnostic,),
                facts={
                    "diagnostic_code": diagnostic.code.value,
                    "sheet_name": diagnostic.sheet_name,
                    "row_number": diagnostic.row_number,
                    "column": diagnostic.column,
                    "verification_mode": VerificationMode.LOCATION,
                },
            )
        )
    total = int(context.execution_statistics.get("records_rejected", 0))
    unlocated = max(total - located_rejections, 0)
    output.observations["rejected_rows_located"] = located_rejections
    output.observations["rejected_rows_unlocated"] = unlocated
    if unlocated:
        key = f"exec:rejected-unlocated:{context.snapshot_id}"
        output.detections.append(
            Detection(
                rule_key=definition.key,
                rule_version=definition.version,
                scope=DetectionScope.EXECUTION,
                review_key=key,
                base_key=key,
                base_key_count=1,
                sheet_month=None,
                facts={
                    "unlocated_rows": unlocated,
                    "verification_mode": VerificationMode.LOCATION,
                },
            )
        )
    return output


def evaluate_unit_missing(
    definition: RuleDefinition, index: ReviewIndex, context: RuleContext
) -> RuleOutput:
    del context
    excluded = frozenset(definition.correctable_fields)
    keys = record_keys(index.records, excluded)
    output = RuleOutput(
        verification_keys=dict(Counter(key.base_key for key in keys.values()))
    )
    for record in index.records:
        if _text(record.administrative_unit) is not None:
            continue
        key = keys[record.id]
        output.detections.append(
            Detection(
                rule_key=definition.key,
                rule_version=definition.version,
                scope=DetectionScope.RECORD,
                review_key=key.review_key,
                base_key=key.base_key,
                base_key_count=key.base_count,
                sheet_month=record.sheet_month,
                record_ids=(record.id,),
                facts={
                    "field": "administrative_unit",
                    "sheet_name": record.sheet_name,
                    "row_number": record.row_number,
                    "physical_date_blank": record.physical_date_blank,
                    "verification_mode": VerificationMode.RECORD,
                },
                impact=_impact(
                    record.amounts.get("final_amount"),
                    "UNATTRIBUTED_FINAL_AMOUNT",
                    ImpactStatus.EXACT,
                ),
            )
        )
    return output


def evaluate_exact_duplicates(
    definition: RuleDefinition, index: ReviewIndex, context: RuleContext
) -> RuleOutput:
    del context
    output = RuleOutput(
        verification_keys={
            f"dup:{month:02d}:{fingerprint}": len(members)
            for (month, fingerprint), members in index.by_fingerprint.items()
        }
    )
    for (month, fingerprint), members in sorted(
        index.by_fingerprint.items(),
        key=lambda item: (item[0][0], item[1][0].row_number),
    ):
        if len(members) < 2:
            continue
        key = f"dup:{month:02d}:{fingerprint}"
        final = members[0].amounts.get("final_amount")
        exposure = None if final is None else final * (len(members) - 1)
        output.detections.append(
            Detection(
                rule_key=definition.key,
                rule_version=definition.version,
                scope=DetectionScope.RECORD_GROUP,
                review_key=key,
                base_key=key,
                base_key_count=len(members),
                sheet_month=month,
                record_ids=tuple(member.id for member in members),
                facts={
                    "occurrences": len(members),
                    "document_present": _text(members[0].document_number) is not None,
                    "sheet_name": members[0].sheet_name,
                    "verification_mode": VerificationMode.GROUP,
                },
                impact=_impact(
                    exposure, "SUM_FINAL_AMOUNT_BEYOND_FIRST", ImpactStatus.CONDITIONAL
                ),
            )
        )
    return output


def _label_drift(
    definition: RuleDefinition,
    groups: Mapping[str, Sequence[tuple[ReviewRecord, str]]],
    *,
    scope: DetectionScope,
    key_prefix: str,
    code_fact: str,
    reference: Mapping[str, str] | None,
) -> RuleOutput:
    output = RuleOutput()
    for code in sorted(groups):
        members = groups[code]
        labels = sorted({label for _record, label in members})
        output.verification_keys[f"{key_prefix}:{code}"] = len(labels)
        if len(labels) < 2:
            continue
        representatives: dict[tuple[int, str], ReviewRecord] = {}
        for record, label in members:
            representatives.setdefault((record.sheet_month, label), record)
        key = f"{key_prefix}:{code}"
        authoritative = None
        if reference is not None:
            candidate = _text(reference.get(code))
            authoritative = candidate
        output.detections.append(
            Detection(
                rule_key=definition.key,
                rule_version=definition.version,
                scope=scope,
                review_key=key,
                base_key=key,
                base_key_count=1,
                sheet_month=None,
                record_ids=tuple(
                    record.id
                    for record in sorted(
                        representatives.values(),
                        key=lambda item: (item.sheet_month, item.row_number),
                    )
                ),
                facts={
                    code_fact: code,
                    "label_count": len(labels),
                    "record_count": len(members),
                    "sheet_count": len({record.sheet_month for record, _ in members}),
                    "verification_mode": VerificationMode.LABEL,
                },
                candidate_values=tuple(labels),
                authoritative_value=authoritative,
            )
        )
    return output


def evaluate_account_label_drift(
    definition: RuleDefinition, index: ReviewIndex, context: RuleContext
) -> RuleOutput:
    groups: dict[str, list[tuple[ReviewRecord, str]]] = {}
    for code, records in index.by_account.items():
        groups[code] = [
            (record, _text(record.account_label) or "") for record in records
        ]
    return _label_drift(
        definition,
        groups,
        scope=DetectionScope.ACCOUNT,
        key_prefix="acct",
        code_fact="account_code",
        reference=context.account_label_reference,
    )


def evaluate_unit_label_drift(
    definition: RuleDefinition, index: ReviewIndex, context: RuleContext
) -> RuleOutput:
    del context
    groups: dict[str, list[tuple[ReviewRecord, str]]] = defaultdict(list)
    unparsed = 0
    for record in index.records:
        unit = _text(record.administrative_unit)
        if unit is None:
            continue
        match = UNIT_PATTERN.fullmatch(unit)
        if match is None:
            unparsed += 1
            continue
        groups[match.group(1)].append((record, match.group(2).strip()))
    output = _label_drift(
        definition,
        groups,
        scope=DetectionScope.UNIT,
        key_prefix="unit",
        code_fact="unit_code",
        reference=None,
    )
    output.observations["units_without_code_pattern"] = unparsed
    return output


# ---------------------------------------------------------------------------
# EXPERIMENTAL rules: observations only, never detections
# ---------------------------------------------------------------------------


def evaluate_hierarchy_reconciliation(
    definition: RuleDefinition, index: ReviewIndex, context: RuleContext
) -> RuleOutput:
    del definition
    parents: Counter[int] = Counter()
    children: Counter[int] = Counter()
    rejected: Counter[int] = Counter()
    for diagnostic in index.diagnostics:
        month = sheet_month(diagnostic.sheet_name or "") or 0
        if diagnostic.code is DiagnosticCode.PARENT_ROW_WITHOUT_CHILD_MATCH:
            parents[month] += 1
        elif diagnostic.code is DiagnosticCode.CHILD_ROW_WITHOUT_PARENT_MATCH:
            children[month] += 1
        elif _is_rejection(diagnostic):
            rejected[month] += 1
    months = sorted(set(parents) | set(children))
    observations: dict[str, int] = {
        "parent_rows_without_child_match": sum(parents.values()),
        "child_rows_without_parent_match": sum(children.values()),
        "sheets_with_hierarchy_difference": len(months),
        "sheets_with_hierarchy_difference_and_rejected_rows": sum(
            1 for month in months if rejected[month]
        ),
        # A value-changed copy leaves one parent and one child unmatched. Rows
        # beyond that pairing have no counterpart on the other level at all.
        "parent_rows_beyond_pairing": sum(
            max(parents[month] - children[month], 0) for month in months
        ),
        "child_rows_beyond_pairing": sum(
            max(children[month] - parents[month], 0) for month in months
        ),
        "diagnostics_truncated": int(
            context.execution_statistics.get("diagnostics_total", 0)
            > context.execution_statistics.get("diagnostics_stored", 0)
        ),
    }
    for month in months:
        observations[f"month_{month:02d}_parent_unmatched"] = parents[month]
        observations[f"month_{month:02d}_child_unmatched"] = children[month]
    return RuleOutput(observations=observations)


def evaluate_near_duplicates(
    definition: RuleDefinition, index: ReviewIndex, context: RuleContext
) -> RuleOutput:
    del definition, context
    groups: dict[tuple[object, ...], set[str]] = defaultdict(set)
    sizes: Counter[tuple[object, ...]] = Counter()
    for record in index.records:
        document = _text(record.document_number)
        if document is None:
            continue
        key = (
            record.sheet_month,
            record.account_code,
            record.emission_date,
            document,
            tuple(_canonical(record.amounts.get(name)) for name in AMOUNT_FIELDS),
        )
        groups[key].add(record.fingerprint)
        sizes[key] += 1
    near = [key for key, fingerprints in groups.items() if len(fingerprints) > 1]
    return RuleOutput(
        observations={
            "near_duplicate_groups": len(near),
            "near_duplicate_records": sum(sizes[key] for key in near),
        }
    )


def evaluate_emission_after_sheet(
    definition: RuleDefinition, index: ReviewIndex, context: RuleContext
) -> RuleOutput:
    del definition, context
    after = 0
    other_year = 0
    for month, records in index.by_month.items():
        years = Counter(record.emission_date.year for record in records)
        dominant = max(years.items(), key=lambda item: (item[1], item[0]))[0]
        for record in records:
            year = record.emission_date.year
            if year != dominant:
                other_year += 1
            if year > dominant or (
                year == dominant and record.emission_date.month > month
            ):
                after += 1
    return RuleOutput(
        observations={
            "emission_after_sheet_month": after,
            "emission_outside_dominant_year": other_year,
        }
    )


def evaluate_final_absent(
    definition: RuleDefinition, index: ReviewIndex, context: RuleContext
) -> RuleOutput:
    del definition, context
    zero = 0
    absent = 0
    for record in index.records:
        movement = record.amounts.get("movement_amount")
        if movement is None or movement == 0:
            continue
        final = record.amounts.get("final_amount")
        if final is None:
            absent += 1
        elif final == 0:
            zero += 1
    return RuleOutput(
        observations={
            "final_zero_with_movement": zero,
            "final_absent_with_movement": absent,
        }
    )


def evaluate_document_missing(
    definition: RuleDefinition, index: ReviewIndex, context: RuleContext
) -> RuleOutput:
    del definition, context
    missing = sum(
        1 for record in index.records if _text(record.document_number) is None
    )
    return RuleOutput(
        observations={
            "records_without_document": missing,
            "records_with_document": len(index.records) - missing,
        }
    )


RuleExecutor = Callable[[RuleDefinition, ReviewIndex, RuleContext], RuleOutput]

DEFAULT_EXECUTORS: dict[str, RuleExecutor] = {
    "NGF-SRC-ROW-REJECTED.v1": evaluate_rejected_rows,
    "NGF-UNIT-MISSING.v1": evaluate_unit_missing,
    "NGF-DUP-EXACT.v1": evaluate_exact_duplicates,
    "NGF-ACCT-LABEL-DRIFT.v1": evaluate_account_label_drift,
    "NGF-UNIT-LABEL-DRIFT.v1": evaluate_unit_label_drift,
    "NGF-HIER-RECONCILIATION.v1": evaluate_hierarchy_reconciliation,
    "NGF-DUP-NEAR.v1": evaluate_near_duplicates,
    "NGF-DATE-EMISSION-AFTER-SHEET.v1": evaluate_emission_after_sheet,
    "NGF-AMT-FINAL-ABSENT.v1": evaluate_final_absent,
    "NGF-DOC-MISSING.v1": evaluate_document_missing,
}
