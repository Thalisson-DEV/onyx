"""SECURITY-08 / TON-SEC-007-A — provider custom_config encryption at rest.

Covers revision ``714172b66b07``, which moves ``llm_provider.custom_config`` and
``voice_provider.custom_config`` from plaintext JSONB to the repository's
``EncryptedJson`` representation.

Real Postgres is required: the point of most assertions is what the *stored
bytes* look like, which a mock cannot show. Raw reads bypass the type decorator
using the same ``cast(LargeBinary)`` technique as
``tests/external_dependency_unit/db/test_rotate_encryption_key.py``.

Every credential-shaped value here is a synthetic sentinel created inside the
test. No real provider credential is read, written or printed.

Run with::

    uv run --env-file .vscode/.env pytest \
        backend/tests/external_dependency_unit/ton/test_provider_secret_encryption.py
"""

import json
import uuid
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import LargeBinary, create_engine, select, text
from sqlalchemy.orm import Session

from ee.onyx.utils.encryption import _get_trimmed_key
from onyx.configs import app_configs
from onyx.db.engine.shard_registry import ALEMBIC_TARGET_URL_ATTRIBUTE
from onyx.db.engine.sql_engine import SYNC_DB_API, build_connection_string
from onyx.db.models import LLMProvider, VoiceProvider
from onyx.db.rotate_encryption_key import _discover_encrypted_columns
from onyx.llm.custom_config_masking import mask_custom_config
from onyx.server.manage.llm.models import LLMProviderView
from onyx.utils.sensitive import SensitiveAccessError, read_sensitive_dict
from onyx.utils.variable_functionality import (
    fetch_versioned_implementation,
    global_version,
)

EE_ENCRYPTION_MODULE = "ee.onyx.utils.encryption"
MIGRATION_MODULE = "alembic.versions.714172b66b07_encrypt_provider_custom_config"

REVISION_003A = "714172b66b07"
REVISION_BEFORE_003A = "ad99acb9be41"

# Synthetic keys. Length only has to clear the EE 16-byte minimum.
TEST_KEY = "t" * 32
WRONG_KEY = "w" * 32

# Synthetic sentinels. Distinctive enough that a substring search over raw bytes
# is a meaningful assertion.
SENTINEL_KNOWN_KEY = "AWS_SECRET_ACCESS_KEY"
SENTINEL_KNOWN_VALUE = "synthetic-known-secret-4a91c7"
# The readiness gate's core point: custom_config accepts arbitrary keys, so a
# key name the deployment has never seen must still be protected.
SENTINEL_UNKNOWN_KEY = "vale_norte_unlisted_field"
SENTINEL_UNKNOWN_VALUE = "synthetic-unknown-secret-b83f20"
NON_SECRET_KEY = "AWS_REGION_NAME"
NON_SECRET_VALUE = "sa-east-1"


def _synthetic_custom_config() -> dict[str, str]:
    return {
        SENTINEL_KNOWN_KEY: SENTINEL_KNOWN_VALUE,
        SENTINEL_UNKNOWN_KEY: SENTINEL_UNKNOWN_VALUE,
        NON_SECRET_KEY: NON_SECRET_VALUE,
    }


@pytest.fixture(autouse=True)
def _encryption_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    """EE encryption resolution plus a synthetic key, as a real deployment has."""
    previous_is_ee = global_version._is_ee
    global_version.set_ee()
    fetch_versioned_implementation.cache_clear()
    _get_trimmed_key.cache_clear()

    monkeypatch.setattr(app_configs, "ENCRYPTION_KEY_SECRET", TEST_KEY)
    monkeypatch.setattr(
        "ee.onyx.utils.encryption.ENCRYPTION_KEY_SECRET", TEST_KEY, raising=False
    )

    yield

    global_version._is_ee = previous_is_ee
    fetch_versioned_implementation.cache_clear()
    _get_trimmed_key.cache_clear()


def _raw_column_bytes(
    db_session: Session, table: Any, row_id: int, column_name: str
) -> bytes | None:
    """Read a column's stored bytes, bypassing the type decorator."""
    col = table.__table__.c[column_name]
    return db_session.execute(
        select(col.cast(LargeBinary)).where(table.__table__.c.id == row_id)
    ).scalar()


@pytest.fixture()
def llm_provider_id(
    db_session: Session,
    tenant_context: None,  # noqa: ARG001
) -> Generator[int, None, None]:
    provider = LLMProvider(
        name=f"ton-003a-llm-{uuid.uuid4().hex[:8]}",
        provider="bedrock",
        custom_config=_synthetic_custom_config(),
        is_public=True,
    )
    db_session.add(provider)
    db_session.commit()
    provider_id = provider.id

    yield provider_id

    db_session.execute(
        text("DELETE FROM llm_provider WHERE id = :id"), {"id": provider_id}
    )
    db_session.commit()


@pytest.fixture()
def voice_provider_id(
    db_session: Session,
    tenant_context: None,  # noqa: ARG001
) -> Generator[int, None, None]:
    provider = VoiceProvider(
        name=f"ton-003a-voice-{uuid.uuid4().hex[:8]}",
        provider_type="azure",
        custom_config=_synthetic_custom_config(),
    )
    db_session.add(provider)
    db_session.commit()
    provider_id = provider.id

    yield provider_id

    db_session.execute(
        text("DELETE FROM voice_provider WHERE id = :id"), {"id": provider_id}
    )
    db_session.commit()


class TestStorageIsEncrypted:
    """1, 5 — stored bytes never hold the synthetic plaintext, before or after update."""

    def test_llm_provider_raw_bytes_are_not_plaintext(
        self, db_session: Session, llm_provider_id: int
    ) -> None:
        raw = _raw_column_bytes(
            db_session, LLMProvider, llm_provider_id, "custom_config"
        )
        assert raw is not None
        assert SENTINEL_KNOWN_VALUE.encode() not in raw
        assert SENTINEL_UNKNOWN_VALUE.encode() not in raw
        # Not merely reordered JSON: the key names are gone too.
        assert SENTINEL_UNKNOWN_KEY.encode() not in raw

    def test_voice_provider_raw_bytes_are_not_plaintext(
        self, db_session: Session, voice_provider_id: int
    ) -> None:
        raw = _raw_column_bytes(
            db_session, VoiceProvider, voice_provider_id, "custom_config"
        )
        assert raw is not None
        assert SENTINEL_KNOWN_VALUE.encode() not in raw
        assert SENTINEL_UNKNOWN_VALUE.encode() not in raw

    def test_update_stays_encrypted(
        self, db_session: Session, llm_provider_id: int
    ) -> None:
        rotated_value = "synthetic-rotated-secret-71ee05"
        provider = db_session.get(LLMProvider, llm_provider_id)
        assert provider is not None
        provider.custom_config = {  # ty: ignore[invalid-assignment]
            SENTINEL_KNOWN_KEY: rotated_value
        }
        db_session.commit()

        raw = _raw_column_bytes(
            db_session, LLMProvider, llm_provider_id, "custom_config"
        )
        assert raw is not None
        assert rotated_value.encode() not in raw

        db_session.expire_all()
        refreshed = db_session.get(LLMProvider, llm_provider_id)
        assert refreshed is not None
        assert read_sensitive_dict(refreshed.custom_config, apply_mask=False) == {
            SENTINEL_KNOWN_KEY: rotated_value
        }


class TestRoundTrip:
    """2, 10 — the runtime, including a background reader, gets the original dict."""

    def test_orm_round_trip_returns_original_dict(
        self, db_session: Session, llm_provider_id: int
    ) -> None:
        db_session.expire_all()
        provider = db_session.get(LLMProvider, llm_provider_id)
        assert provider is not None
        assert (
            read_sensitive_dict(provider.custom_config, apply_mask=False)
            == _synthetic_custom_config()
        )

    def test_voice_orm_round_trip_returns_original_dict(
        self, db_session: Session, voice_provider_id: int
    ) -> None:
        db_session.expire_all()
        provider = db_session.get(VoiceProvider, voice_provider_id)
        assert provider is not None
        assert (
            read_sensitive_dict(provider.custom_config, apply_mask=False)
            == _synthetic_custom_config()
        )

    def test_independent_session_can_decrypt(self, llm_provider_id: int) -> None:
        """A worker opening its own session decrypts the same configuration.

        Stands in for the Celery readers, which reach providers the same way:
        a fresh session, no request context.
        """
        engine = create_engine(build_connection_string(db_api=SYNC_DB_API))
        try:
            with Session(engine) as worker_session:
                provider = worker_session.get(LLMProvider, llm_provider_id)
                assert provider is not None
                assert (
                    read_sensitive_dict(provider.custom_config, apply_mask=False)
                    == _synthetic_custom_config()
                )
        finally:
            engine.dispose()

    def test_llm_provider_view_exposes_plain_dict_to_the_runtime(
        self, db_session: Session, llm_provider_id: int
    ) -> None:
        """The LLM factory builds from this view, so it must hold a real dict."""
        db_session.expire_all()
        provider = db_session.get(LLMProvider, llm_provider_id)
        assert provider is not None
        view = LLMProviderView.from_model(provider)
        assert view.custom_config == _synthetic_custom_config()


class TestApiMasking:
    """3, 4 — the API boundary masks the whole dict, unknown key names included."""

    def test_masking_hides_known_and_unknown_secret_keys(self) -> None:
        masked = mask_custom_config(_synthetic_custom_config())
        assert masked is not None
        assert masked[SENTINEL_KNOWN_KEY] != SENTINEL_KNOWN_VALUE
        assert masked[SENTINEL_UNKNOWN_KEY] != SENTINEL_UNKNOWN_VALUE
        assert SENTINEL_UNKNOWN_VALUE not in json.dumps(masked)
        # Structure survives so the admin UI can still see what is configured.
        assert set(masked) == set(_synthetic_custom_config())
        # A known setting stays readable; the forms rebuild their state from it.
        assert masked[NON_SECRET_KEY] == NON_SECRET_VALUE

    def test_provider_response_is_masked(
        self, db_session: Session, llm_provider_id: int
    ) -> None:
        from onyx.server.manage.llm.api import _mask_provider_credentials

        db_session.expire_all()
        provider = db_session.get(LLMProvider, llm_provider_id)
        assert provider is not None
        view = LLMProviderView.from_model(provider)
        _mask_provider_credentials(view)

        serialized = view.model_dump_json()
        assert SENTINEL_KNOWN_VALUE not in serialized
        assert SENTINEL_UNKNOWN_VALUE not in serialized

    def test_voice_provider_response_is_masked(
        self, db_session: Session, voice_provider_id: int
    ) -> None:
        from onyx.server.manage.voice.api import _provider_to_view

        db_session.expire_all()
        provider = db_session.get(VoiceProvider, voice_provider_id)
        assert provider is not None
        serialized = _provider_to_view(provider).model_dump_json()
        assert SENTINEL_KNOWN_VALUE not in serialized
        assert SENTINEL_UNKNOWN_VALUE not in serialized


class TestSerializationDoesNotLeak:
    """9 — nothing on the accidental paths (str, repr, log, JSON) exposes the value."""

    def test_repr_and_str_do_not_expose(
        self, db_session: Session, llm_provider_id: int
    ) -> None:
        db_session.expire_all()
        provider = db_session.get(LLMProvider, llm_provider_id)
        assert provider is not None
        wrapped = provider.custom_config
        assert wrapped is not None

        assert SENTINEL_UNKNOWN_VALUE not in repr(wrapped)
        with pytest.raises(SensitiveAccessError):
            str(wrapped)
        with pytest.raises(SensitiveAccessError):
            _ = wrapped[SENTINEL_UNKNOWN_KEY]
        with pytest.raises(SensitiveAccessError):
            list(iter(wrapped))

    def test_logging_the_model_does_not_expose(
        self,
        db_session: Session,
        llm_provider_id: int,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        import logging

        db_session.expire_all()
        provider = db_session.get(LLMProvider, llm_provider_id)
        assert provider is not None

        with caplog.at_level(logging.INFO):
            logging.getLogger(__name__).info(
                "provider custom_config=%r", provider.custom_config
            )

        assert SENTINEL_KNOWN_VALUE not in caplog.text
        assert SENTINEL_UNKNOWN_VALUE not in caplog.text


class TestWrongKeyFailsSafely:
    """8 — a wrong key raises; it never yields garbage, plaintext or raw bytes."""

    def test_wrong_key_raises_and_leaves_the_row_intact(
        self,
        db_session: Session,
        llm_provider_id: int,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        raw_before = _raw_column_bytes(
            db_session, LLMProvider, llm_provider_id, "custom_config"
        )

        db_session.expire_all()
        monkeypatch.setattr(
            "ee.onyx.utils.encryption.ENCRYPTION_KEY_SECRET", WRONG_KEY, raising=False
        )
        _get_trimmed_key.cache_clear()

        provider = db_session.get(LLMProvider, llm_provider_id)
        assert provider is not None
        wrapped = provider.custom_config
        assert wrapped is not None

        with pytest.raises((ValueError, UnicodeDecodeError)):
            wrapped.get_value(apply_mask=False)

        # The failure did not rewrite, clear or truncate the stored value.
        monkeypatch.setattr(
            "ee.onyx.utils.encryption.ENCRYPTION_KEY_SECRET", TEST_KEY, raising=False
        )
        _get_trimmed_key.cache_clear()
        assert (
            _raw_column_bytes(db_session, LLMProvider, llm_provider_id, "custom_config")
            == raw_before
        )


class TestRotationDiscovery:
    """11 — key rotation picks the converted columns up with no rotation change."""

    def test_rotation_discovers_both_converted_columns(self) -> None:
        discovered = {
            (
                model_cls.__tablename__,  # ty: ignore[unresolved-attribute]
                column_name,
                is_json,
            )
            for model_cls, column_name, _, is_json in _discover_encrypted_columns()
        }
        assert ("llm_provider", "custom_config", True) in discovered
        assert ("voice_provider", "custom_config", True) in discovered


# ---------------------------------------------------------------------------
# Migration-level coverage. Each case runs against its own throwaway database,
# so the migration is exercised for real without touching the test database.
# ---------------------------------------------------------------------------


def _admin_engine() -> Any:
    return create_engine(
        build_connection_string(db_api=SYNC_DB_API), isolation_level="AUTOCOMMIT"
    )


def _drop_database(name: str) -> None:
    engine = _admin_engine()
    try:
        with engine.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
    finally:
        engine.dispose()


@contextmanager
def _scratch_database(template: str | None = None) -> Iterator[str]:
    """Yield a throwaway database, dropped afterwards.

    Cloning from *template* skips replaying the whole revision chain, which the
    guard tests would otherwise pay for once each.
    """
    name = f"onyx_ton_003a_{uuid.uuid4().hex[:12]}"
    engine = _admin_engine()
    try:
        with engine.connect() as connection:
            statement = f'CREATE DATABASE "{name}"'
            if template is not None:
                statement += f' TEMPLATE "{template}"'
            connection.execute(text(statement))
    finally:
        engine.dispose()
    try:
        yield name
    finally:
        _drop_database(name)


@pytest.fixture(scope="module")
def pre_003a_template() -> Generator[str, None, None]:
    """A database at the revision immediately before 003a, used as a clone source."""
    name = f"onyx_ton_003a_tmpl_{uuid.uuid4().hex[:8]}"
    engine = _admin_engine()
    try:
        with engine.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        engine.dispose()
    try:
        command.upgrade(_alembic_config(name), REVISION_BEFORE_003A)
        yield name
    finally:
        _drop_database(name)


def _alembic_config(database: str) -> AlembicConfig:
    config = AlembicConfig("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.attributes[ALEMBIC_TARGET_URL_ATTRIBUTE] = build_connection_string(
        db=database
    )
    config.attributes["configure_logger"] = False
    return config


def _sync_engine(database: str) -> Any:
    return create_engine(build_connection_string(db_api=SYNC_DB_API, db=database))


def _custom_config_sql_type(database: str, table_name: str) -> str:
    engine = _sync_engine(database)
    try:
        with engine.connect() as connection:
            return connection.execute(
                text(
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_name = :table AND column_name = 'custom_config'"
                ),
                {"table": table_name},
            ).scalar_one()
    finally:
        engine.dispose()


def _seed_plaintext_providers(database: str) -> None:
    """Insert synthetic pre-003a rows straight into the plaintext JSONB columns."""
    engine = _sync_engine(database)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO llm_provider (name, provider, custom_config, "
                    "is_public, is_auto_mode) "
                    "VALUES (:name, 'bedrock', CAST(:cfg AS jsonb), true, false)"
                ),
                {
                    "name": "ton-003a-migration-llm",
                    "cfg": json.dumps(_synthetic_custom_config()),
                },
            )
            connection.execute(
                text(
                    "INSERT INTO voice_provider (name, provider_type, custom_config, "
                    "is_default_stt, is_default_tts) "
                    "VALUES (:name, 'azure', CAST(:cfg AS jsonb), false, false)"
                ),
                {
                    "name": "ton-003a-migration-voice",
                    "cfg": json.dumps(_synthetic_custom_config()),
                },
            )
    finally:
        engine.dispose()


def _raw_custom_config_blobs(database: str, table_name: str) -> list[bytes | None]:
    engine = _sync_engine(database)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    f"SELECT custom_config::text FROM {table_name} "  # noqa: S608
                    "WHERE custom_config IS NOT NULL"
                )
            ).all()
        return [None if row[0] is None else str(row[0]).encode() for row in rows]
    finally:
        engine.dispose()


class TestMigrationGuards:
    """6, 7 — the migration aborts before converting anything when either
    invariant is unmet, and the plaintext rows survive untouched."""

    def test_missing_encryption_key_aborts_and_preserves_plaintext(
        self, pre_003a_template: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with _scratch_database(pre_003a_template) as database:
            _seed_plaintext_providers(database)

            monkeypatch.setattr(app_configs, "ENCRYPTION_KEY_SECRET", "")
            with pytest.raises(RuntimeError, match="ENCRYPTION_KEY_SECRET"):
                command.upgrade(_alembic_config(database), REVISION_003A)

            # Aborted before the type change, with the rows still present.
            assert _custom_config_sql_type(database, "llm_provider") == "jsonb"
            assert len(_raw_custom_config_blobs(database, "llm_provider")) == 1

    def test_community_encryption_aborts_and_preserves_plaintext(
        self, pre_003a_template: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with _scratch_database(pre_003a_template) as database:
            _seed_plaintext_providers(database)

            # Resolve the Community implementation the way a CE process would.
            monkeypatch.setattr(
                "onyx.utils.variable_functionality.ENTERPRISE_EDITION_ENABLED", False
            )
            monkeypatch.setattr(
                "onyx.utils.variable_functionality._LICENSE_ENFORCEMENT_ENABLED", False
            )
            global_version.unset_ee()
            fetch_versioned_implementation.cache_clear()

            with pytest.raises(RuntimeError, match="Enterprise Edition"):
                command.upgrade(_alembic_config(database), REVISION_003A)

            assert _custom_config_sql_type(database, "llm_provider") == "jsonb"
            assert len(_raw_custom_config_blobs(database, "llm_provider")) == 1

    def test_database_without_provider_rows_reaches_head_without_a_key(
        self, pre_003a_template: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No stored configuration means nothing to protect and nothing to abort.

        This is what keeps CI and a fresh install able to migrate; the
        base-to-head path itself is covered by the pytest-alembic gate.
        """
        with _scratch_database(pre_003a_template) as database:
            monkeypatch.setattr(app_configs, "ENCRYPTION_KEY_SECRET", "")
            command.upgrade(_alembic_config(database), REVISION_003A)
            assert _custom_config_sql_type(database, "llm_provider") == "bytea"
            assert _custom_config_sql_type(database, "voice_provider") == "bytea"


class TestMigrationTransition:
    """The negative control, the data transition and the lossy downgrade."""

    def test_plaintext_becomes_unreadable_and_survives_the_transition(
        self, pre_003a_template: str
    ) -> None:
        with _scratch_database(pre_003a_template) as database:
            _seed_plaintext_providers(database)

            # Before: the raw database value is readable credential JSON.
            for table_name in ("llm_provider", "voice_provider"):
                before = _raw_custom_config_blobs(database, table_name)
                assert len(before) == 1
                assert before[0] is not None
                assert SENTINEL_UNKNOWN_VALUE.encode() in before[0]

            command.upgrade(_alembic_config(database), REVISION_003A)

            # After: the row is still there, and no longer readable.
            for table_name in ("llm_provider", "voice_provider"):
                assert _custom_config_sql_type(database, table_name) == "bytea"
                after = _raw_custom_config_blobs(database, table_name)
                assert len(after) == 1, "the provider row must not be deleted"
                assert after[0] is not None
                assert SENTINEL_KNOWN_VALUE.encode() not in after[0]
                assert SENTINEL_UNKNOWN_VALUE.encode() not in after[0]
                assert SENTINEL_UNKNOWN_KEY.encode() not in after[0]

            # The transitioned value decrypts back to what was stored.
            engine = _sync_engine(database)
            try:
                with engine.connect() as connection:
                    stored = connection.execute(
                        text(
                            "SELECT custom_config FROM llm_provider "
                            "WHERE custom_config IS NOT NULL"
                        )
                    ).scalar_one()
            finally:
                engine.dispose()

            from onyx.utils.encryption import decrypt_bytes_to_string

            assert (
                json.loads(decrypt_bytes_to_string(bytes(stored)))
                == _synthetic_custom_config()
            )

    def test_downgrade_is_lossy_and_never_decrypts(
        self, pre_003a_template: str
    ) -> None:
        with _scratch_database(pre_003a_template) as database:
            _seed_plaintext_providers(database)
            command.upgrade(_alembic_config(database), REVISION_003A)

            command.downgrade(_alembic_config(database), REVISION_BEFORE_003A)

            for table_name in ("llm_provider", "voice_provider"):
                assert _custom_config_sql_type(database, table_name) == "jsonb"
                # Empty, not plaintext: a downgrade is not a decryption oracle.
                assert _raw_custom_config_blobs(database, table_name) == []

            engine = _sync_engine(database)
            try:
                with engine.connect() as connection:
                    remaining = connection.execute(
                        text("SELECT count(*) FROM llm_provider")
                    ).scalar_one()
            finally:
                engine.dispose()
            assert remaining == 1, "the provider row itself must survive a downgrade"
