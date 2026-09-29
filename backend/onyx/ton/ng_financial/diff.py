"""Structural comparison of two parsed NG exports. No business judgement.

The export has no official row identifier, so matching is heuristic:

1. Records with the same content fingerprint in the same month are unchanged.
   Exact duplicates pair in physical row order.
2. Remaining records pair when at least ``MIN_IDENTITY_MATCHES`` of the
   identity fields agree. Best score wins; ties break by row order. A tie at the
   best score is reported as ambiguous.
3. Everything else is added or removed.

Row numbers and sheet names are never part of the identity: an inserted row
shifts every later row without changing content.
"""

from collections import Counter, defaultdict
from collections.abc import Callable, Hashable

from onyx.ton.ng_financial.models import (
    ChangedPair,
    MonthDiff,
    ParsedImportResult,
    ParsedSourceRecordData,
    RecordLocation,
    SourceDiff,
)
from onyx.ton.ng_financial.parser import AMOUNT_FIELDS, COLUMNS

IDENTITY_FIELDS = (
    "account_code",
    "emission_date",
    "administrative_unit",
    "document_number",
    "history",
)
COMPARED_FIELDS = (*IDENTITY_FIELDS, "account_label", *AMOUNT_FIELDS)
MIN_IDENTITY_MATCHES = 3
CONTRACT_COLUMNS = frozenset(COLUMNS)


def _field_values(record: ParsedSourceRecordData) -> dict[str, object]:
    values = record.model_dump(include=set(COMPARED_FIELDS))
    values["source_extras"] = sorted(
        (column, value)
        for column, value in record.source_values.items()
        if column not in CONTRACT_COLUMNS
    )
    return values


def _location(record: ParsedSourceRecordData) -> RecordLocation:
    assert record.locator.sheet_name is not None
    assert record.locator.row_number is not None
    return RecordLocation(
        month=record.sheet_month,
        sheet_name=record.locator.sheet_name,
        row_number=record.locator.row_number,
    )


def _row(record: ParsedSourceRecordData) -> int:
    return record.locator.row_number or 0


BLOCKING_KEYS: tuple[Callable[[ParsedSourceRecordData], Hashable | None], ...] = (
    lambda record: record.document_number,
    lambda record: record.history,
    lambda record: (record.account_code, record.emission_date),
)


def _compare_month(
    month: int,
    left: list[ParsedSourceRecordData],
    right: list[ParsedSourceRecordData],
    diff: SourceDiff,
    changed_fields: Counter[str],
) -> None:
    left = sorted(left, key=_row)
    right = sorted(right, key=_row)
    right_by_fingerprint: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(right):
        right_by_fingerprint[record.fingerprint].append(index)
    unchanged = 0
    left_rest: list[int] = []
    used_right: set[int] = set()
    for index, record in enumerate(left):
        bucket = right_by_fingerprint.get(record.fingerprint)
        if bucket:
            used_right.add(bucket.pop(0))
            unchanged += 1
        else:
            left_rest.append(index)
    right_rest = [index for index in range(len(right)) if index not in used_right]

    indexes: list[dict[Hashable, list[int]]] = []
    for key in BLOCKING_KEYS:
        index_map: dict[Hashable, list[int]] = defaultdict(list)
        for position in right_rest:
            value = key(right[position])
            if value is not None:
                index_map[value].append(position)
        indexes.append(index_map)

    left_values = {position: _field_values(left[position]) for position in left_rest}
    right_values = {position: _field_values(right[position]) for position in right_rest}
    # (negative score, left row, right row, left position, right position)
    candidates: list[tuple[int, int, int, int, int]] = []
    ambiguous = 0
    for position in left_rest:
        record = left[position]
        seen: set[int] = set()
        for key, index_map in zip(BLOCKING_KEYS, indexes, strict=True):
            value = key(record)
            if value is not None:
                seen.update(index_map.get(value, ()))
        scores: list[int] = []
        for other in sorted(seen):
            identity = sum(
                left_values[position][name] == right_values[other][name]
                for name in IDENTITY_FIELDS
            )
            if identity < MIN_IDENTITY_MATCHES:
                continue
            score = identity * 100 + sum(
                left_values[position][name] == right_values[other][name]
                for name in AMOUNT_FIELDS
            )
            scores.append(score)
            candidates.append(
                (-score, _row(record), _row(right[other]), position, other)
            )
        if scores and scores.count(max(scores)) > 1:
            ambiguous += 1
    # Deterministic greedy assignment: best score, then earliest rows.
    assigned_left: set[int] = set()
    assigned_right: set[int] = set()
    pairs: list[tuple[int, int]] = []
    for *_order, position, other in sorted(candidates):
        if position in assigned_left or other in assigned_right:
            continue
        assigned_left.add(position)
        assigned_right.add(other)
        pairs.append((position, other))
    for position, other in sorted(pairs, key=lambda pair: _row(left[pair[0]])):
        fields = tuple(
            name
            for name in (*COMPARED_FIELDS, "source_extras")
            if left_values[position][name] != right_values[other][name]
        )
        changed_fields.update(fields)
        diff.changed_pairs.append(
            ChangedPair(
                left=_location(left[position]),
                right=_location(right[other]),
                fields=fields,
            )
        )
    removed = [left[p] for p in left_rest if p not in assigned_left]
    added = [right[p] for p in right_rest if p not in assigned_right]
    diff.removed.extend(_location(record) for record in removed)
    diff.added.extend(_location(record) for record in added)
    diff.months.append(
        MonthDiff(
            month=month,
            left_records=len(left),
            right_records=len(right),
            unchanged=unchanged,
            changed=len(pairs),
            added=len(added),
            removed=len(removed),
            ambiguous=ambiguous,
        )
    )


def compare_source_imports(
    left: ParsedImportResult, right: ParsedImportResult
) -> SourceDiff:
    by_month_left: dict[int, list[ParsedSourceRecordData]] = defaultdict(list)
    by_month_right: dict[int, list[ParsedSourceRecordData]] = defaultdict(list)
    for record in left.records:
        by_month_left[record.sheet_month].append(record)
    for record in right.records:
        by_month_right[record.sheet_month].append(record)
    diff = SourceDiff(
        months=[], changed_pairs=[], added=[], removed=[], changed_fields={}
    )
    changed_fields: Counter[str] = Counter()
    for month in sorted(by_month_left.keys() | by_month_right.keys()):
        _compare_month(
            month,
            by_month_left.get(month, []),
            by_month_right.get(month, []),
            diff,
            changed_fields,
        )
    diff.changed_fields = dict(sorted(changed_fields.items()))
    return diff
