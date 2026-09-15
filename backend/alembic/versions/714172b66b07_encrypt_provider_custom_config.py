"""encrypt provider custom config

Revision ID: 714172b66b07
Revises: ad99acb9be41
Create Date: 2026-09-15 07:36:05.945336

Moves provider custom configuration from plaintext ``JSONB`` to the encrypted
``LargeBinary`` representation already used by ``credential.credential_json``
(revision ``0a98909f2757``):

- ``llm_provider.custom_config``
- ``voice_provider.custom_config``

Both dicts carry provider credentials — AWS Bedrock keys, Vertex service-account
JSON, LM Studio bearer tokens — so they must not stay readable in a plain
``SELECT``. Rows are re-encrypted in place. No provider row is deleted and no
credential is reset, unlike revision ``b4950827c0dd``, which could drop rows only
because that feature had no production data.

Two guards run before any credential row is written. The Community
``_encrypt_string`` returns ``input_str.encode()``: it stores cleartext while the
schema claims the column is encrypted, and the EE read path decodes such a row
without raising, so there is no read-time signal. Converting under those
conditions is worse than leaving the column as JSONB. The conversion therefore
requires both:

1. the EE encryption implementation to resolve, and
2. ``ENCRYPTION_KEY_SECRET`` to be present and to round-trip.

The guards are gated on there being at least one row to convert. An empty
database — CI, a fresh install — holds no credential to protect and reaches head
without a key.

``downgrade`` is deliberately lossy. It drops the encrypted column and recreates
an empty ``JSONB`` column; it never decrypts, so a downgrade cannot be used as a
decryption oracle. Operators re-enter provider custom configuration through the
admin UI afterwards.
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection

# Imported as a module, not a name, so the value is read when the guard runs
# rather than snapshotted at import time.
from onyx.configs import app_configs
from onyx.utils.encryption import decrypt_bytes_to_string, encrypt_string_to_bytes
from onyx.utils.variable_functionality import (
    fetch_versioned_implementation,
    global_version,
)

# revision identifiers, used by Alembic.
revision = "714172b66b07"
down_revision = "ad99acb9be41"
branch_labels = None
depends_on = None


TARGET_TABLES = ("llm_provider", "voice_provider")
TARGET_COLUMN = "custom_config"
TEMP_COLUMN = "custom_config_encrypted"

# Fixed probe text used to prove encryption is real. Never a credential value.
_ENCRYPTION_PROBE = "onyx-003a-encryption-probe"

_EE_ENCRYPTION_MODULE = "ee.onyx.utils.encryption"


def _provider_table(table_name: str) -> sa.Table:
    """Lightweight table literal. The application ORM must not be imported here."""
    return sa.Table(
        table_name,
        sa.MetaData(),
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(TARGET_COLUMN, postgresql.JSONB(astext_type=sa.Text())),
        sa.Column(TEMP_COLUMN, sa.LargeBinary),
    )


def _rows_needing_conversion(connection: Connection) -> int:
    """Count provider rows holding a non-null plaintext configuration."""
    total = 0
    for table_name in TARGET_TABLES:
        table = _provider_table(table_name)
        total += (
            connection.execute(
                sa.select(sa.func.count())
                .select_from(table)
                .where(table.c[TARGET_COLUMN].is_not(None))
            ).scalar_one()
            or 0
        )
    return total


def require_real_encryption() -> None:
    """Raise unless encryption genuinely protects what this migration writes.

    Both invariants are checked, then proved by a round-trip on fixed probe text.
    One is not sufficient: EE without a key, and a key without EE, both store
    cleartext.
    """
    if not global_version.is_ee_version():
        raise RuntimeError(
            "Provider custom_config encryption requires the Enterprise Edition "
            "encryption implementation. The Community implementation stores "
            "cleartext, so this migration would claim the column is encrypted "
            "while leaving credentials readable. Aborting before any row is "
            "converted."
        )

    encrypt_fn = fetch_versioned_implementation(
        "onyx.utils.encryption", "_encrypt_string"
    )
    resolved_module = encrypt_fn.__module__ or ""
    if resolved_module != _EE_ENCRYPTION_MODULE:
        raise RuntimeError(
            "Provider custom_config encryption resolved "
            f"'{resolved_module}' instead of '{_EE_ENCRYPTION_MODULE}'. "
            "Aborting before any row is converted."
        )

    if not app_configs.ENCRYPTION_KEY_SECRET:
        raise RuntimeError(
            "ENCRYPTION_KEY_SECRET is not set. Inject the deployment encryption "
            "key before upgrading, otherwise provider credentials would be "
            "written as plaintext bytes into a column the schema calls "
            "encrypted. Aborting before any row is converted."
        )

    probe_bytes = encrypt_string_to_bytes(_ENCRYPTION_PROBE)
    if probe_bytes == _ENCRYPTION_PROBE.encode():
        raise RuntimeError(
            "The encryption round-trip returned the input unchanged, so nothing "
            "would be protected. Aborting before any row is converted."
        )
    if decrypt_bytes_to_string(probe_bytes) != _ENCRYPTION_PROBE:
        raise RuntimeError(
            "The encryption round-trip did not reproduce its input. Verify "
            "ENCRYPTION_KEY_SECRET. Aborting before any row is converted."
        )


def upgrade() -> None:
    connection = op.get_bind()

    # Guard first: nothing is altered unless encryption is proven, and an empty
    # database has no credential at risk.
    if _rows_needing_conversion(connection) > 0:
        require_real_encryption()

    for table_name in TARGET_TABLES:
        op.add_column(
            table_name, sa.Column(TEMP_COLUMN, sa.LargeBinary(), nullable=True)
        )

        table = _provider_table(table_name)
        rows = connection.execute(
            sa.select(table.c.id, table.c[TARGET_COLUMN]).where(
                table.c[TARGET_COLUMN].is_not(None)
            )
        ).all()

        for row_id, custom_config in rows:
            connection.execute(
                table.update()
                .where(table.c.id == row_id)
                .values(
                    {
                        TEMP_COLUMN: encrypt_string_to_bytes(
                            json.dumps(custom_config, sort_keys=True)
                        )
                    }
                )
            )

        # Transition safety: no plaintext row may reach the drop without an
        # encrypted counterpart. Raising here rolls the whole revision back.
        unconverted = (
            connection.execute(
                sa.select(sa.func.count())
                .select_from(table)
                .where(table.c[TARGET_COLUMN].is_not(None))
                .where(table.c[TEMP_COLUMN].is_(None))
            ).scalar_one()
            or 0
        )
        if unconverted:
            raise RuntimeError(
                f"{unconverted} {table_name}.{TARGET_COLUMN} row(s) were not "
                "encrypted. Aborting so no configuration is dropped."
            )

        op.drop_column(table_name, TARGET_COLUMN)
        op.alter_column(table_name, TEMP_COLUMN, new_column_name=TARGET_COLUMN)


def downgrade() -> None:
    # Deliberately lossy. The encrypted representation is dropped and an empty
    # nullable JSONB column takes its place, matching the pre-upgrade schema
    # contract. Values are never decrypted back into plaintext, so a downgrade
    # cannot serve as a decryption oracle (same reasoning as revision
    # 0a98909f2757). Operators must re-enter provider custom configuration —
    # including Bedrock keys, Vertex credentials and LM Studio tokens — through
    # the admin UI after downgrading.
    for table_name in TARGET_TABLES:
        op.drop_column(table_name, TARGET_COLUMN)
        op.add_column(
            table_name,
            sa.Column(
                TARGET_COLUMN,
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )
