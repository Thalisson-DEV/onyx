"""``ton-canon-1`` and the RuleVersion definition hash (Plan 003d).

Unit tests, not integration ones: :mod:`onyx.db.ton.canonical` is pure — no
session, no I/O — and the definition-hash functions take an unpersisted
:class:`RuleVersion`, so a database would add nothing but time. The database-level
report behaviour lives in
``tests/external_dependency_unit/ton/test_report_immutability.py``.

Every assertion here is about one of the ten guarantees readiness §12 requires of
the canonical form, and each test name says which.
"""

import datetime
from decimal import Decimal

import pytest

from onyx.db.ton.canonical import (
    CANONICALIZATION_VERSION,
    HASH_ALGORITHM,
    MAX_DECIMAL_SCALE,
    ScaledDecimal,
    canonical_decimal_text,
    canonical_document,
    canonical_text,
    canonical_timestamp_text,
    compute_content_hash,
)
from onyx.db.ton.enums import (
    EvidenceConfidenceLevel,
    MissingDataBehavior,
    PostResolutionPolicy,
    RuleProvenance,
    RuleVersionStatus,
    TonReportType,
)
from onyx.db.ton.models import RuleVersion
from onyx.db.ton.rule_versions import (
    RULE_VERSION_DEFINITION_FIELDS,
    RULE_VERSION_NON_DEFINITION_COLUMNS,
    compute_definition_hash,
    definition_hash_matches,
    rule_version_definition_payload,
)

SYNTHETIC_EXECUTOR_KEY = "synthetic_noop_executor.v1"


def _rule_version(**overrides: object) -> RuleVersion:
    """An unpersisted rule version. Enough for the pure hashing contract."""
    defaults: dict[str, object] = {
        "version": 1,
        "title": "Synthetic rule version",
        "description": None,
        "executor_key": SYNTHETIC_EXECUTOR_KEY,
        "parameters": {"synthetic_threshold": "0.5", "synthetic_window": 7},
        "unit": None,
        "currency": None,
        "scale": None,
        "rounding_mode": None,
        "applicability": {},
        "effective_from": None,
        "effective_to": None,
        "source_reference": None,
        "provenance": RuleProvenance.DERIVED,
        "missing_data_behavior": MissingDataBehavior.SKIP_WITH_NOTE,
        "evidence_requirements": {},
        "min_confidence_level": EvidenceConfidenceLevel.C,
        "severity_mapping": {},
        "nc_code": None,
        "identity_components": ["rule_code", "period"],
        "post_resolution_policy": PostResolutionPolicy.REOPEN_SAME_OCCURRENCE,
    }
    defaults.update(overrides)
    return RuleVersion(**defaults)


class TestCanonicalScheme:
    def test_the_scheme_and_algorithm_are_the_approved_ones(self) -> None:
        """Readiness §12 names both. They are values, not implementation detail:
        each is persisted next to every hash so a future change cannot invalidate
        a digest already recorded."""
        assert CANONICALIZATION_VERSION == "ton-canon-1"
        assert HASH_ALGORITHM == "sha256"

    def test_the_hash_is_a_sha256_hex_digest(self) -> None:
        digest = compute_content_hash({"a": 1})
        assert len(digest) == 64
        assert set(digest) <= set("0123456789abcdef")


class TestKeyOrdering:
    def test_insertion_order_does_not_alter_the_hash(self) -> None:
        """Guarantee 8. Two dictionaries built in different orders are one
        payload."""
        first = {"zulu": 1, "alpha": 2, "mike": 3}
        second = {"mike": 3, "zulu": 1, "alpha": 2}
        assert compute_content_hash(first) == compute_content_hash(second)

    def test_keys_are_emitted_in_sorted_order(self) -> None:
        assert canonical_text({"b": 1, "a": 2, "c": 3}) == '{"a":2,"b":1,"c":3}'

    def test_nested_object_keys_are_sorted_too(self) -> None:
        assert canonical_text({"outer": {"b": 1, "a": 2}}) == '{"outer":{"a":2,"b":1}}'

    def test_array_order_is_preserved(self) -> None:
        """Sorting a list would change the payload's meaning, so only object keys
        are ordered."""
        assert canonical_text({"xs": [3, 1, 2]}) == '{"xs":[3,1,2]}'

    def test_there_is_no_insignificant_whitespace(self) -> None:
        assert " " not in canonical_text({"a": {"b": [1, 2]}})


class TestMonetaryAndDecimalValues:
    def test_a_monetary_value_is_a_decimal_string_never_a_json_number(self) -> None:
        """Guarantees 1 and 4, the load-bearing rules of this domain."""
        text = canonical_text({"amount": ScaledDecimal(Decimal("1234.50"), scale=2)})
        assert text == '{"amount":"1234.50"}'

    def test_a_declared_scale_pads_trailing_zeros(self) -> None:
        assert canonical_decimal_text(Decimal("10.5"), scale=2) == "10.50"
        assert canonical_decimal_text(Decimal("7"), scale=4) == "7.0000"

    def test_equal_values_at_one_declared_scale_agree(self) -> None:
        """``10.5`` and ``10.500`` are the same number, so at scale 2 they are one
        canonical form and one hash."""
        first = ScaledDecimal(Decimal("10.5"), scale=2)
        second = ScaledDecimal(Decimal("10.500"), scale=2)
        assert compute_content_hash({"a": first}) == compute_content_hash({"a": second})

    def test_two_declared_scales_are_two_published_values(self) -> None:
        """The scale is part of the published contract: ``10.50`` and ``10.5000``
        state different precision, so they must not share a hash."""
        two = ScaledDecimal(Decimal("10.5"), scale=2)
        four = ScaledDecimal(Decimal("10.5"), scale=4)
        assert compute_content_hash({"a": two}) != compute_content_hash({"a": four})

    def test_a_bare_decimal_normalises_so_equal_values_agree(self) -> None:
        assert compute_content_hash({"a": Decimal("10.50")}) == compute_content_hash(
            {"a": Decimal("10.5")}
        )

    def test_a_decimal_and_its_string_form_hash_identically(self) -> None:
        """Readiness's explicit case: a monetary value must never round-trip
        through a float, asserted by hashing it as ``Decimal`` and as a string."""
        as_decimal = ScaledDecimal(Decimal("1234.50"), scale=2)
        assert compute_content_hash({"a": as_decimal}) == compute_content_hash(
            {"a": "1234.50"}
        )

    def test_a_percentage_is_a_decimal_string(self) -> None:
        text = canonical_text({"pct": ScaledDecimal(Decimal("12.5"), scale=4)})
        assert text == '{"pct":"12.5000"}'

    def test_a_quantity_needing_exact_semantics_is_a_decimal_string(self) -> None:
        text = canonical_text({"litres": ScaledDecimal(Decimal("1500.125"), scale=3)})
        assert text == '{"litres":"1500.125"}'

    def test_negative_zero_and_zero_are_one_representation(self) -> None:
        assert canonical_decimal_text(Decimal("-0.00"), scale=2) == "0.00"
        assert compute_content_hash({"a": Decimal("-0")}) == compute_content_hash(
            {"a": Decimal("0")}
        )

    def test_a_value_too_precise_for_its_scale_is_refused_not_rounded(self) -> None:
        """Silently rounding a published figure is the class of error Prompt
        Mestre §6 exists for."""
        with pytest.raises(ValueError, match="without rounding"):
            canonical_decimal_text(Decimal("10.555"), scale=2)

    def test_a_scale_beyond_the_column_width_is_refused(self) -> None:
        with pytest.raises(ValueError, match="between 0 and"):
            ScaledDecimal(Decimal("1"), scale=MAX_DECIMAL_SCALE + 1)

    def test_a_non_finite_decimal_has_no_canonical_form(self) -> None:
        with pytest.raises(ValueError, match="no canonical decimal form"):
            compute_content_hash({"a": Decimal("NaN")})

    def test_an_integer_count_stays_a_json_number(self) -> None:
        """An int is exact, so a count or an ordinal needs no string form. A
        business decimal must still arrive as Decimal or ScaledDecimal."""
        assert canonical_text({"rows": 3}) == '{"rows":3}'


class TestFloatRejection:
    def test_a_float_is_rejected_outright(self) -> None:
        with pytest.raises(ValueError, match="no canonical form"):
            compute_content_hash({"amount": 1234.5})

    def test_accumulated_float_error_is_not_silently_coerced(self) -> None:
        """``0.1 + 0.2`` is not ``0.3``. Refusing it is the whole point: coercing
        it would record an exact-looking decimal that no other platform derives."""
        assert 0.1 + 0.2 != 0.3
        with pytest.raises(ValueError, match="IEEE-754"):
            compute_content_hash({"total": 0.1 + 0.2})

    def test_a_nested_float_is_rejected_too(self) -> None:
        with pytest.raises(ValueError, match="no canonical form"):
            compute_content_hash({"body": {"rows": [{"amount": 1.5}]}})

    def test_a_scaled_decimal_refuses_a_float_value(self) -> None:
        """The type checker rejects this too. The runtime guard exists because a
        value arriving from JSONB carries no static type at all."""
        with pytest.raises(ValueError, match="must not be a float"):
            ScaledDecimal(0.5, scale=2)  # ty: ignore[invalid-argument-type]

    def test_raw_bytes_are_rejected(self) -> None:
        """Publishing source material rather than a reference to it."""
        with pytest.raises(ValueError, match="Raw bytes"):
            compute_content_hash({"blob": b"abc"})


class TestTimestamps:
    def test_a_utc_timestamp_carries_an_explicit_z(self) -> None:
        """Guarantee 5."""
        moment = datetime.datetime(2026, 1, 2, 12, 0, tzinfo=datetime.UTC)
        assert canonical_timestamp_text(moment) == "2026-01-02T12:00:00.000000Z"

    def test_offset_equivalent_instants_canonicalise_identically(self) -> None:
        utc = datetime.datetime(2026, 1, 2, 12, 0, tzinfo=datetime.UTC)
        offset = datetime.datetime(
            2026, 1, 2, 9, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=-3))
        )
        assert compute_content_hash({"t": utc}) == compute_content_hash({"t": offset})

    def test_precision_is_fixed_so_one_instant_has_one_form(self) -> None:
        without = datetime.datetime(2026, 1, 2, 12, 0, 0, tzinfo=datetime.UTC)
        with_zeros = datetime.datetime(2026, 1, 2, 12, 0, 0, 0, tzinfo=datetime.UTC)
        assert compute_content_hash({"t": without}) == compute_content_hash(
            {"t": with_zeros}
        )

    def test_a_naive_timestamp_is_refused_rather_than_assumed_utc(self) -> None:
        """Assuming would make the canonical form depend on where the process
        happened to run."""
        with pytest.raises(ValueError, match="timezone-aware"):
            canonical_timestamp_text(datetime.datetime(2026, 1, 2, 12, 0))

    def test_a_date_is_iso_without_a_time(self) -> None:
        assert canonical_text({"d": datetime.date(2026, 1, 2)}) == '{"d":"2026-01-02"}'


class TestEnums:
    def test_an_enum_serialises_as_its_value(self) -> None:
        """Guarantee 6, matching the repository's ``native_enum=False``
        convention."""
        text = canonical_text({"type": TonReportType.HIDDEN_MONEY_PANEL})
        assert text == '{"type":"HIDDEN_MONEY_PANEL"}'

    def test_an_enum_and_its_string_value_hash_identically(self) -> None:
        assert compute_content_hash(
            {"type": TonReportType.MONTHLY_CLOSE}
        ) == compute_content_hash({"type": "MONTHLY_CLOSE"})

    def test_every_ton_report_type_is_stable(self) -> None:
        """Name equals value, so a CHECK constraint written against the literal
        string stays correct whichever storage convention a reader assumes."""
        for member in TonReportType:
            assert member.name == member.value
            assert canonical_text({"t": member}) == f'{{"t":"{member.value}"}}'


class TestAbsentValues:
    def test_an_absent_key_is_omitted_not_written_as_null(self) -> None:
        """Guarantee 7."""
        assert canonical_text({"a": 1, "b": None}) == '{"a":1}'

    def test_omitting_a_key_and_setting_it_to_null_normalise_to_one_form(self) -> None:
        """Readiness requires the two to be either refused as ambiguous or
        normalised. Normalising is the simpler contract, so absence wins."""
        assert compute_content_hash({"a": 1, "b": None}) == compute_content_hash(
            {"a": 1}
        )

    def test_null_inside_an_array_is_refused_as_ambiguous(self) -> None:
        """Dropping it would shift every later element, so it cannot be treated as
        absence."""
        with pytest.raises(ValueError, match="must not contain null"):
            compute_content_hash({"xs": [1, None, 2]})

    def test_a_present_empty_string_is_not_absence(self) -> None:
        assert compute_content_hash({"a": ""}) != compute_content_hash({})


class TestUnicode:
    def test_composed_and_decomposed_text_canonicalise_identically(self) -> None:
        """Guarantee 9. RFC 8785 fixes escaping but not composition, so NFC is a
        TON rule on top — the same precedent ``ton-id-1`` set for identity keys."""
        composed = "\u00e9"
        decomposed = "e\u0301"
        assert composed != decomposed
        assert compute_content_hash({"k": composed}) == compute_content_hash(
            {"k": decomposed}
        )

    def test_keys_are_normalised_as_well_as_values(self) -> None:
        assert compute_content_hash({"caf\u00e9": 1}) == compute_content_hash(
            {"cafe\u0301": 1}
        )

    def test_two_keys_that_normalise_alike_are_refused(self) -> None:
        with pytest.raises(ValueError, match="normalise to"):
            compute_content_hash({"caf\u00e9": 1, "cafe\u0301": 2})

    def test_non_ascii_text_is_emitted_as_utf8_not_escaped(self) -> None:
        assert canonical_text({"k": "ação"}) == '{"k":"ação"}'

    def test_control_characters_use_the_rfc_8785_escapes(self) -> None:
        assert canonical_text({"k": 'a\nb\tc"d\\e'}) == '{"k":"a\\nb\\tc\\"d\\\\e"}'

    def test_a_non_string_key_is_refused(self) -> None:
        with pytest.raises(ValueError, match="key must be a string"):
            compute_content_hash({1: "a"})  # ty: ignore[invalid-argument-type]


class TestCanonicalDocument:
    def test_the_document_holds_only_json_native_types(self) -> None:
        """Why this function exists: the stored JSONB and the hashed bytes must be
        the same thing, so the document form is produced once and used for both."""
        document = canonical_document(
            {
                "amount": ScaledDecimal(Decimal("1.5"), scale=2),
                "when": datetime.datetime(2026, 1, 2, tzinfo=datetime.UTC),
                "day": datetime.date(2026, 1, 2),
                "type": TonReportType.ISC,
                "rows": 2,
                "flag": True,
                "absent": None,
            }
        )
        assert document == {
            "amount": "1.50",
            "day": "2026-01-02",
            "flag": True,
            "rows": 2,
            "type": "ISC",
            "when": "2026-01-02T00:00:00.000000Z",
        }

    def test_the_document_hashes_the_same_as_its_source(self) -> None:
        payload = {"amount": ScaledDecimal(Decimal("1.5"), scale=2), "n": 1}
        assert compute_content_hash(
            canonical_document(payload)
        ) == compute_content_hash(payload)

    def test_a_json_round_trip_preserves_the_hash(self) -> None:
        """The property that makes hash verification on read possible: PostgreSQL
        reorders JSONB keys, and the canonicalisation sorts them again."""
        import json

        payload = {
            "z": ScaledDecimal(Decimal("2.25"), scale=2),
            "a": {"inner": datetime.date(2026, 5, 6)},
        }
        document = canonical_document(payload)
        reordered = dict(reversed(list(json.loads(json.dumps(document)).items())))
        assert compute_content_hash(reordered) == compute_content_hash(payload)

    def test_a_non_mapping_payload_is_refused(self) -> None:
        with pytest.raises(ValueError, match="mapping at the top level"):
            canonical_document([1, 2])  # ty: ignore[invalid-argument-type]


class TestRuleVersionDefinitionHash:
    def test_the_hash_is_scheme_prefixed(self) -> None:
        """Unlike ``TonReportRevision.content_hash``, which stores its scheme in a
        column, ``definition_hash`` has no companion column — so the scheme travels
        inside the value and a future change is visible instead of silent."""
        digest = compute_definition_hash(_rule_version(), rule_code="SYN-RULE-1")
        assert digest.startswith(f"{CANONICALIZATION_VERSION}:")
        assert len(digest.split(":", 1)[1]) == 64

    def test_the_payload_holds_exactly_the_declared_definition_fields(self) -> None:
        payload = rule_version_definition_payload(
            _rule_version(), rule_code="SYN-RULE-1"
        )
        assert set(payload) == set(RULE_VERSION_DEFINITION_FIELDS)

    def test_the_same_definition_hashes_identically(self) -> None:
        first = compute_definition_hash(_rule_version(), rule_code="SYN-RULE-1")
        second = compute_definition_hash(_rule_version(), rule_code="SYN-RULE-1")
        assert first == second

    def test_a_changed_threshold_changes_the_hash(self) -> None:
        baseline = compute_definition_hash(_rule_version(), rule_code="SYN-RULE-1")
        changed = compute_definition_hash(
            _rule_version(parameters={"synthetic_threshold": "0.6"}),
            rule_code="SYN-RULE-1",
        )
        assert baseline != changed

    def test_a_changed_rule_code_changes_the_hash(self) -> None:
        assert compute_definition_hash(
            _rule_version(), rule_code="SYN-RULE-1"
        ) != compute_definition_hash(_rule_version(), rule_code="SYN-RULE-2")

    def test_approval_state_does_not_change_the_hash(self) -> None:
        """The decisive exclusion. Approving a version does not redefine it, so a
        hash that moved on approval would make the tamper check useless."""
        import uuid

        draft = _rule_version()
        approved = _rule_version(
            status=RuleVersionStatus.ACTIVE,
            approved_by=uuid.uuid4(),
            approved_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            approval_reference="SYN-APPROVAL-1",
        )
        assert compute_definition_hash(
            draft, rule_code="SYN-RULE-1"
        ) == compute_definition_hash(approved, rule_code="SYN-RULE-1")

    def test_storage_facts_do_not_change_the_hash(self) -> None:
        """The same definition stored at another time, by another account, under
        another surrogate id must hash the same."""
        import uuid

        stored_now = _rule_version()
        stored_now.id = uuid.uuid4()
        stored_now.rule_id = uuid.uuid4()
        stored_now.created_by = uuid.uuid4()
        stored_now.created_at = datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC)

        stored_later = _rule_version()
        stored_later.id = uuid.uuid4()
        stored_later.rule_id = uuid.uuid4()
        stored_later.created_by = uuid.uuid4()
        stored_later.created_at = datetime.datetime(2026, 9, 9, tzinfo=datetime.UTC)

        assert compute_definition_hash(
            stored_now, rule_code="SYN-RULE-1"
        ) == compute_definition_hash(stored_later, rule_code="SYN-RULE-1")

    def test_the_excluded_columns_are_stated_and_disjoint(self) -> None:
        overlap = RULE_VERSION_NON_DEFINITION_COLUMNS & set(
            RULE_VERSION_DEFINITION_FIELDS
        )
        assert overlap == set()

    def test_every_rule_version_column_is_classified(self) -> None:
        """An inverse assertion: a column added later must be deliberately placed
        in or out of the canonical definition, not silently omitted."""
        columns = set(RuleVersion.__table__.columns.keys())
        classified = set(RULE_VERSION_DEFINITION_FIELDS) | (
            RULE_VERSION_NON_DEFINITION_COLUMNS
        )
        # `rule_code` replaces `rule_id` in the payload, so it is not a column.
        assert columns - classified == set()

    def test_identity_component_order_does_not_change_the_hash(self) -> None:
        """Two versions declaring the same dimensions declare one definition."""
        forward = _rule_version(identity_components=["rule_code", "period"])
        reversed_order = _rule_version(identity_components=["period", "rule_code"])
        assert compute_definition_hash(
            forward, rule_code="SYN-RULE-1"
        ) == compute_definition_hash(reversed_order, rule_code="SYN-RULE-1")

    def test_a_float_threshold_is_refused_rather_than_hashed(self) -> None:
        """A threshold stored as an IEEE-754 double is not exactly reproducible,
        so recording tamper evidence over it would be a lie."""
        with pytest.raises(ValueError, match="no canonical form"):
            compute_definition_hash(
                _rule_version(parameters={"synthetic_threshold": 0.5}),
                rule_code="SYN-RULE-1",
            )

    def test_a_missing_rule_code_is_refused(self) -> None:
        with pytest.raises(ValueError, match="rule_code is required"):
            compute_definition_hash(_rule_version(), rule_code="  ")

    def test_an_unhashed_row_never_passes_the_tamper_check(self) -> None:
        """Absence of evidence is not evidence of integrity."""
        rule_version = _rule_version()
        rule_version.definition_hash = None
        assert definition_hash_matches(rule_version, rule_code="SYN-RULE-1") is False

    def test_a_matching_hash_passes_and_a_tampered_definition_fails(self) -> None:
        rule_version = _rule_version()
        rule_version.definition_hash = compute_definition_hash(
            rule_version, rule_code="SYN-RULE-1"
        )
        assert definition_hash_matches(rule_version, rule_code="SYN-RULE-1") is True

        rule_version.parameters = {"synthetic_threshold": "9.9"}
        assert definition_hash_matches(rule_version, rule_code="SYN-RULE-1") is False
