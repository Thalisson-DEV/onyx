"""Masking and restore for provider ``custom_config`` dicts.

``custom_config`` accepts arbitrary keys, so a key-name heuristic cannot decide
what holds a credential: a secret stored under an unrecognised name would be
returned to the client in full. Masking here is therefore whole-dict by default.
Every value is masked unless its key appears in
``NON_CREDENTIAL_CUSTOM_CONFIG_KEYS`` — the small set of keys that are known to
carry configuration rather than credentials, and that the admin forms read back
to rebuild their state.

Structure is preserved: every key stays present, so a client can still tell that
configuration exists and which entries are set. Only the values are hidden.

``restore_masked_custom_config`` is the exact inverse used on the write path. It
must stay symmetric with ``mask_custom_config``: any key the mask covers must be
restorable, otherwise saving an unmodified form would persist the placeholder
over the real credential.
"""

from typing import Any

from onyx.llm.custom_config_mapping import UI_ONLY_CONFIG_KEYS
from onyx.llm.well_known_providers.constants import (
    AWS_REGION_NAME_KWARG,
    AWS_REGION_NAME_KWARG_ENV_VAR_FORMAT,
    VERTEX_AUTH_METHOD_KWARG,
    VERTEX_LOCATION_KWARG,
    VERTEX_PROJECT_KWARG,
)
from onyx.utils.encryption import mask_string as mask_with_ellipsis

# Placeholder for a masked value that is not a string. Keeps the key visible
# without hinting at the stored content.
MASKED_VALUE_PLACEHOLDER = "*****"

# Placeholders a client may echo back instead of the value it was shown.
_ADDITIONAL_MASK_PLACEHOLDERS = frozenset(
    {"****", "••••••••••••", "***REDACTED***", MASKED_VALUE_PLACEHOLDER}
)

# Voice provider configuration keys. Regional endpoint selection and the STT
# language list are settings, not credentials, and the voice admin form reads
# both back to preserve entries it does not own.
_VOICE_CONFIG_KEYS = frozenset({"speech_region", "stt_languages"})

# Keys whose values are configuration rather than credential material. Compared
# case-insensitively, because the same setting appears in both kwarg and
# environment-variable spelling.
NON_CREDENTIAL_CUSTOM_CONFIG_KEYS: frozenset[str] = frozenset(
    key.lower()
    for key in (
        *UI_ONLY_CONFIG_KEYS,
        AWS_REGION_NAME_KWARG,
        AWS_REGION_NAME_KWARG_ENV_VAR_FORMAT,
        "AWS_REGION",
        VERTEX_AUTH_METHOD_KWARG,
        VERTEX_LOCATION_KWARG,
        VERTEX_PROJECT_KWARG,
        *_VOICE_CONFIG_KEYS,
    )
)


def is_non_credential_custom_config_key(key: str) -> bool:
    """True when ``key`` is a known setting and its value may be returned as-is.

    Everything else is treated as credential material, including keys this
    deployment has never seen.
    """
    return key.lower() in NON_CREDENTIAL_CUSTOM_CONFIG_KEYS


def mask_provider_secret(value: str) -> str:
    """Mask a secret, showing the first and last four characters."""
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


def _mask_value(value: Any) -> Any:
    if isinstance(value, str):
        # An empty value carries nothing to hide, and masking it would make
        # "unset" look configured.
        return mask_provider_secret(value) if value else value
    if isinstance(value, dict):
        return {key: _mask_value(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_mask_value(item) for item in value]
    if isinstance(value, (bool, type(None))):
        return value
    return MASKED_VALUE_PLACEHOLDER


def mask_custom_config(
    custom_config: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Mask every ``custom_config`` value except the known non-credential keys."""
    if custom_config is None:
        return None
    return {
        key: value if is_non_credential_custom_config_key(key) else _mask_value(value)
        for key, value in custom_config.items()
    }


def is_masked_custom_config_value(
    incoming_value: Any, existing_value: Any, key: str
) -> bool:
    """True when ``incoming_value`` is the masked form of ``existing_value``."""
    if is_non_credential_custom_config_key(key):
        return False
    if not isinstance(incoming_value, str):
        return incoming_value == _mask_value(existing_value)
    if incoming_value in _ADDITIONAL_MASK_PLACEHOLDERS:
        return True
    if not isinstance(existing_value, str):
        return False
    return incoming_value in {
        mask_provider_secret(existing_value),
        mask_with_ellipsis(existing_value),
    }


def restore_masked_custom_config(
    existing_custom_config: dict[str, Any] | None,
    new_custom_config: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Swap masked placeholders back for the stored values they stand for.

    Inverse of ``mask_custom_config``. Values the caller actually changed pass
    through untouched, so an edit still overwrites the stored credential.
    """
    if not existing_custom_config or not new_custom_config:
        return new_custom_config

    restored = dict(new_custom_config)
    for key, incoming_value in restored.items():
        if key not in existing_custom_config:
            continue
        existing_value = existing_custom_config[key]
        if is_masked_custom_config_value(incoming_value, existing_value, key):
            restored[key] = existing_value

    return restored
