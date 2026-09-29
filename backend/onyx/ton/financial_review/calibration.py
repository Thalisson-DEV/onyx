"""Development calibration: TON findings on ORIGINAL versus a reviewed version.

Never used by the review engine. The reviewed version is a historical human
review, not truth: a delta TON did not flag may need a source TON lacks, and a
TON finding the reviewer did not act on is a TON-only candidate, not an error.

Output is counts and group signatures only. No value, history or document
leaves this module.
"""

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from onyx.ton.ng_financial.diff import compare_source_imports
from onyx.ton.ng_financial.models import (
    ParsedImportResult,
    ParsedSourceRecordData,
    RecordLocation,
)


class FieldDeltaGroup(StrEnum):
    DATE = "DATE"
    UNIT = "UNIT"
    DOCUMENT = "DOCUMENT"
    HISTORY = "HISTORY"
    CLASSIFICATION = "CLASSIFICATION"
    MONETARY = "MONETARY"
    INTEREST = "INTEREST"
    PENALTY = "PENALTY"
    DISCOUNT = "DISCOUNT"
    RETENTION = "RETENTION"
    NET = "NET"
    FINAL_AMOUNT = "FINAL_AMOUNT"
    OTHER = "OTHER"


FIELD_GROUPS: dict[str, FieldDeltaGroup] = {
    "emission_date": FieldDeltaGroup.DATE,
    "administrative_unit": FieldDeltaGroup.UNIT,
    "document_number": FieldDeltaGroup.DOCUMENT,
    "history": FieldDeltaGroup.HISTORY,
    "account_code": FieldDeltaGroup.CLASSIFICATION,
    "account_label": FieldDeltaGroup.CLASSIFICATION,
    "movement_amount": FieldDeltaGroup.MONETARY,
    "expense_amount": FieldDeltaGroup.MONETARY,
    "loss_amount": FieldDeltaGroup.MONETARY,
    "other_deduction_amount": FieldDeltaGroup.MONETARY,
    "interest_amount": FieldDeltaGroup.INTEREST,
    "penalty_amount": FieldDeltaGroup.PENALTY,
    "discount_amount": FieldDeltaGroup.DISCOUNT,
    "movement_retention_amount": FieldDeltaGroup.RETENTION,
    "installment_retention_amount": FieldDeltaGroup.RETENTION,
    "movement_net_amount": FieldDeltaGroup.NET,
    "installment_net_amount": FieldDeltaGroup.NET,
    "final_amount": FieldDeltaGroup.FINAL_AMOUNT,
}


def delta_groups(fields: Iterable[str]) -> tuple[FieldDeltaGroup, ...]:
    groups = {FIELD_GROUPS.get(name, FieldDeltaGroup.OTHER) for name in fields}
    order = list(FieldDeltaGroup)
    return tuple(sorted(groups, key=order.index))


def signature(groups: Iterable[FieldDeltaGroup]) -> str:
    return "+".join(item.value for item in groups) or "NONE"


class ChangeStructure(StrEnum):
    # Only the effective date differs, both physical date cells are blank, and
    # the nearest dated row above it in the reviewed block is an added record.
    CARRY_FORWARD_AFTER_ADDED_RECORD = "CARRY_FORWARD_AFTER_ADDED_RECORD"
    FIELD_EDIT = "FIELD_EDIT"


Location = tuple[int, int]


@dataclass(frozen=True)
class MonthCalibration:
    month: int
    unchanged: int
    changed: int
    added: int
    removed: int
    ambiguous: int


@dataclass
class CalibrationReport:
    months: list[MonthCalibration]
    changed_by_signature: dict[str, int]
    changed_by_structure: dict[str, int]
    added_linked_to_carry_forward: int
    reviewed_deltas: int
    deltas_with_ton_finding: int
    deltas_without_ton_finding: int
    unexplained_by_signature: dict[str, int]
    ton_flagged_original_records: int
    ton_only_candidates: int
    ambiguous_matches: int
    ton_rules_on_deltas: dict[str, int] = field(default_factory=dict)


def _location(item: RecordLocation) -> Location:
    return (item.month, item.row_number)


def _by_location(result: ParsedImportResult) -> dict[Location, ParsedSourceRecordData]:
    return {
        (record.sheet_month, record.locator.row_number or 0): record
        for record in result.records
    }


def _nearest_dated_above(
    target: ParsedSourceRecordData, records: Iterable[ParsedSourceRecordData]
) -> ParsedSourceRecordData | None:
    target_row = target.locator.row_number or 0
    candidates = [
        record
        for record in records
        if record.sheet_month == target.sheet_month
        and record.account_code == target.account_code
        and (record.locator.row_number or 0) < target_row
        and record.source_values.get("B") is not None
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda record: record.locator.row_number or 0)


def calibrate(
    original: ParsedImportResult,
    reviewed: ParsedImportResult,
    *,
    ton_flags: Mapping[Location, Iterable[str]],
) -> CalibrationReport:
    """Compare a TON review of ORIGINAL with a historical reviewed version.

    ``ton_flags`` maps an ORIGINAL record location ``(month, row)`` to the rule
    keys of TON findings on it. It must come from a review of ORIGINAL only.
    """
    diff = compare_source_imports(original, reviewed)
    left = _by_location(original)
    right = _by_location(reviewed)
    added = {_location(item) for item in diff.added}
    flags = {location: set(rules) for location, rules in ton_flags.items() if rules}

    by_signature: Counter[str] = Counter()
    by_structure: Counter[str] = Counter()
    unexplained: Counter[str] = Counter()
    rules_on_deltas: Counter[str] = Counter()
    linked_added: set[Location] = set()
    changed_left: set[Location] = set()
    explained = 0

    for pair in diff.changed_pairs:
        groups = delta_groups(pair.fields)
        label = signature(groups)
        by_signature[label] += 1
        left_location = _location(pair.left)
        changed_left.add(left_location)
        structure = ChangeStructure.FIELD_EDIT
        right_record = right.get(_location(pair.right))
        left_record = left.get(left_location)
        if (
            pair.fields == ("emission_date",)
            and right_record is not None
            and left_record is not None
            and right_record.source_values.get("B") is None
            and left_record.source_values.get("B") is None
        ):
            anchor = _nearest_dated_above(right_record, reviewed.records)
            if anchor is not None:
                anchor_location = (anchor.sheet_month, anchor.locator.row_number or 0)
                if anchor_location in added:
                    structure = ChangeStructure.CARRY_FORWARD_AFTER_ADDED_RECORD
                    linked_added.add(anchor_location)
        by_structure[structure.value] += 1
        if left_location in flags:
            explained += 1
            rules_on_deltas.update(flags[left_location])
        else:
            unexplained[label] += 1

    for location in diff.removed:
        if _location(location) in flags:
            explained += 1
            rules_on_deltas.update(flags[_location(location)])
        else:
            unexplained["REMOVED"] += 1
    unexplained["ADDED"] += len(diff.added)
    if not unexplained["ADDED"]:
        del unexplained["ADDED"]

    removed = {_location(item) for item in diff.removed}
    reviewed_deltas = len(diff.changed_pairs) + len(diff.added) + len(diff.removed)
    return CalibrationReport(
        months=[
            MonthCalibration(
                month=item.month,
                unchanged=item.unchanged,
                changed=item.changed,
                added=item.added,
                removed=item.removed,
                ambiguous=item.ambiguous,
            )
            for item in diff.months
        ],
        changed_by_signature=dict(sorted(by_signature.items())),
        changed_by_structure=dict(sorted(by_structure.items())),
        added_linked_to_carry_forward=len(linked_added),
        reviewed_deltas=reviewed_deltas,
        deltas_with_ton_finding=explained,
        deltas_without_ton_finding=reviewed_deltas - explained,
        unexplained_by_signature=dict(sorted(unexplained.items())),
        ton_flagged_original_records=len(flags),
        ton_only_candidates=sum(
            1
            for location in flags
            if location not in changed_left and location not in removed
        ),
        ambiguous_matches=diff.ambiguous,
        ton_rules_on_deltas=dict(sorted(rules_on_deltas.items())),
    )
