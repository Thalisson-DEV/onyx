"""Projections from DATA-002 outputs into engine inputs. No parsing happens here."""

from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from onyx.ton.financial_review.models import ReviewRecord
from onyx.ton.ng_financial.models import ParsedSourceRecordData
from onyx.ton.ng_financial.parser import AMOUNT_FIELDS


def review_record(
    *,
    record_id: UUID,
    sheet_name: str,
    row_number: int,
    sheet_month: int,
    account_code: str,
    account_label: str,
    emission_date: date,
    administrative_unit: str | None,
    document_number: str | None,
    history: str,
    amounts: Mapping[str, Decimal | None],
    physical_date: str | None,
    physical_unit: str | None,
    fingerprint: str,
    duplicate_ordinal: int,
) -> ReviewRecord:
    return ReviewRecord(
        id=record_id,
        sheet_name=sheet_name,
        row_number=row_number,
        sheet_month=sheet_month,
        account_code=account_code,
        account_label=account_label,
        emission_date=emission_date,
        administrative_unit=administrative_unit,
        document_number=document_number,
        history=history,
        amounts={name: amounts.get(name) for name in AMOUNT_FIELDS},
        physical_date_blank=physical_date is None,
        physical_unit_blank=physical_unit is None,
        fingerprint=fingerprint,
        duplicate_ordinal=duplicate_ordinal,
    )


def location_record_id(snapshot_id: UUID, sheet_name: str, row_number: int) -> UUID:
    """Deterministic id for an unpersisted parse result (tests and calibration)."""
    return uuid5(NAMESPACE_URL, f"ton-parse:{snapshot_id}:{sheet_name}:{row_number}")


def review_records_from_parse(
    records: list[ParsedSourceRecordData],
) -> list[ReviewRecord]:
    projected: list[ReviewRecord] = []
    for record in records:
        sheet_name = record.locator.sheet_name or ""
        row_number = record.locator.row_number or 0
        projected.append(
            review_record(
                record_id=location_record_id(
                    record.locator.snapshot_id, sheet_name, row_number
                ),
                sheet_name=sheet_name,
                row_number=row_number,
                sheet_month=record.sheet_month,
                account_code=record.account_code,
                account_label=record.account_label,
                emission_date=record.emission_date,
                administrative_unit=record.administrative_unit,
                document_number=record.document_number,
                history=record.history,
                amounts=record.model_dump(include=set(AMOUNT_FIELDS)),
                physical_date=record.source_values.get("B"),
                physical_unit=record.source_values.get("C"),
                fingerprint=record.fingerprint,
                duplicate_ordinal=record.duplicate_ordinal,
            )
        )
    return projected
