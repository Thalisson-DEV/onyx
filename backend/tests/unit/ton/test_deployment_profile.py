"""TON deployment profile assertions (Plan 007).

Every credential a compose variant needs must be injected from outside the
repository. These tests read the deployment artifacts as text and assert on
variable names and interpolation syntax only. No real or synthetic secret value
is written here, and no assertion ever prints a credential.

The compose files are generated from `docker-compose.template.yml` by
`ods generate-compose --write`, so the tests cover the template and all three
generated variants. A hand edit to a generated file therefore fails here as well
as in the CLI drift test.
"""

import re
from configparser import ConfigParser
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
COMPOSE_DIR = REPO_ROOT / "deployment" / "docker_compose"
EMBEDDED_DIR = (
    REPO_ROOT
    / "cli"
    / "internal"
    / "deploy"
    / "deployfiles"
    / "embedded"
    / "docker_compose"
)

TEMPLATE = COMPOSE_DIR / "docker-compose.template.yml"

# The generator's outputs, keyed by the variant name it renders them from.
GENERATED_VARIANTS = {
    "default": COMPOSE_DIR / "docker-compose.yml",
    "prod": COMPOSE_DIR / "docker-compose.prod.yml",
    "no-letsencrypt": COMPOSE_DIR / "docker-compose.prod-no-letsencrypt.yml",
}

# The production profiles. These additionally require the encryption key.
PRODUCTION_VARIANTS = ("prod", "no-letsencrypt")

# Credentials every variant declares required. Names only; the point of the plan
# is that no value lives here.
REQUIRED_CREDENTIAL_VARS = (
    "OPENSEARCH_ADMIN_PASSWORD",
    "MINIO_ROOT_USER",
    "MINIO_ROOT_PASSWORD",
    "S3_AWS_ACCESS_KEY_ID",
    "S3_AWS_SECRET_ACCESS_KEY",
)

# The database password is set inline only by the default variant. The production
# variants deliberately leave `relational_db` without an environment block so
# `USE_IAM_AUTH=true` deployments, which have no password at all, still render.
# Both routes are covered: required in the default variant, and never defaulted
# anywhere.
DEFAULT_ONLY_REQUIRED_VARS = ("POSTGRES_PASSWORD",)

# Credential-bearing variables the default profile leaves optional, listed so a
# later change has to state its intent rather than silently widen the set.
PRODUCTION_ONLY_REQUIRED_VARS = ("ENCRYPTION_KEY_SECRET",)

# Every credential name this module reasons about.
ALL_CREDENTIAL_VARS = (
    *REQUIRED_CREDENTIAL_VARS,
    *DEFAULT_ONLY_REQUIRED_VARS,
    *PRODUCTION_ONLY_REQUIRED_VARS,
)

# Published defaults that used to ship in the deployment artifacts. They are
# public knowledge, not secrets, and are asserted absent.
PUBLISHED_DEFAULTS = ("StrongPassword123!", "minioadmin")

# Services the TON deployment depends on. Removing one breaks search, storage,
# queues or the web surface.
EXPECTED_SERVICES = (
    "api_server",
    "background",
    "web_server",
    "relational_db",
    "opensearch",
    "cache",
    "minio",
    "nginx",
    "inference_model_server",
    "indexing_model_server",
)

# Supervisor programs that carry the queues, scheduling and monitoring the
# background service runs.
EXPECTED_SUPERVISOR_PROGRAMS = (
    "celery_worker_primary",
    "celery_worker_light",
    "celery_worker_heavy",
    "celery_worker_docprocessing",
    "celery_worker_docfetching",
    "celery_worker_user_file_processing",
    "celery_worker_scheduled_tasks",
    "celery_worker_monitoring",
    "celery_beat",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_compose(path: Path) -> dict:
    document = yaml.safe_load(_read(path))
    assert isinstance(document, dict), f"{path.name} is not a compose mapping"
    return document


def _required_interpolations(text: str) -> set[str]:
    """Variable names the file marks as required (``${NAME:?message}``)."""
    return set(re.findall(r"\$\{([A-Z0-9_]+):\?", text))


def _defaulted_interpolations(text: str) -> set[str]:
    """Variable names the file gives an inline fallback (``${NAME:-value}``)."""
    return set(re.findall(r"\$\{([A-Z0-9_]+):-", text))


# --------------------------------------------------------------------------
# Credential injection
# --------------------------------------------------------------------------


@pytest.mark.parametrize("variant", sorted(GENERATED_VARIANTS))
@pytest.mark.parametrize("variable", REQUIRED_CREDENTIAL_VARS)
def test_credential_requires_external_injection(variant: str, variable: str) -> None:
    """Each credential is declared required in every generated variant.

    ``${NAME:?message}`` makes Docker Compose refuse to start and name the
    missing variable, which is the fail-closed behaviour the plan asks for.
    """
    text = _read(GENERATED_VARIANTS[variant])
    assert variable in _required_interpolations(text), (
        f"{variable} must use ${{{variable}:?...}} in the {variant} variant"
    )


@pytest.mark.parametrize("variable", DEFAULT_ONLY_REQUIRED_VARS)
def test_default_variant_requires_the_database_password(variable: str) -> None:
    assert variable in _required_interpolations(_read(GENERATED_VARIANTS["default"]))


@pytest.mark.parametrize("variant", PRODUCTION_VARIANTS)
@pytest.mark.parametrize("variable", DEFAULT_ONLY_REQUIRED_VARS)
def test_production_variants_do_not_set_the_database_password_inline(
    variant: str, variable: str
) -> None:
    """Production leaves the database credential to `.env` or IAM auth.

    It must still be absent as an inline value, so a rendered file cannot supply
    one on its own.
    """
    services = _load_compose(GENERATED_VARIANTS[variant])["services"]
    assert "environment" not in services["relational_db"], (
        f"{variant} variant now sets relational_db environment inline; "
        "USE_IAM_AUTH deployments have no password to interpolate"
    )
    assert variable not in _defaulted_interpolations(_read(GENERATED_VARIANTS[variant]))


@pytest.mark.parametrize(
    "variant,variable",
    [
        (variant, variable)
        for variant in GENERATED_VARIANTS
        for variable in ALL_CREDENTIAL_VARS
    ],
)
def test_credential_never_carries_an_inline_fallback(
    variant: str, variable: str
) -> None:
    """No credential may resolve from a value rendered into a compose file."""
    text = _read(GENERATED_VARIANTS[variant])
    assert variable not in _defaulted_interpolations(text), (
        f"{variable} has an inline fallback in the {variant} variant"
    )


@pytest.mark.parametrize(
    "variable", [*REQUIRED_CREDENTIAL_VARS, *DEFAULT_ONLY_REQUIRED_VARS]
)
def test_credential_requires_external_injection_in_template(variable: str) -> None:
    """The source template carries the requirement, not just its outputs."""
    text = _read(TEMPLATE)
    assert variable in _required_interpolations(text)
    assert variable not in _defaulted_interpolations(text)


@pytest.mark.parametrize("variant", PRODUCTION_VARIANTS)
@pytest.mark.parametrize("variable", PRODUCTION_ONLY_REQUIRED_VARS)
def test_production_requires_encryption_key(variant: str, variable: str) -> None:
    """Production profiles refuse to start without the at-rest encryption key.

    Without it the encrypted columns (connector credentials, provider API keys,
    bot tokens) are written as plaintext bytes.
    """
    text = _read(GENERATED_VARIANTS[variant])
    assert variable in _required_interpolations(text)
    assert variable not in _defaulted_interpolations(text)


@pytest.mark.parametrize("variable", PRODUCTION_ONLY_REQUIRED_VARS)
def test_default_variant_leaves_encryption_key_optional(variable: str) -> None:
    """The development profile stays usable without the key.

    This is the one credential-bearing variable the default profile does not
    force. It is asserted explicitly so widening or narrowing that boundary is a
    deliberate edit, not a side effect.
    """
    assert variable not in _read(GENERATED_VARIANTS["default"])


@pytest.mark.parametrize(
    "path",
    [TEMPLATE, *GENERATED_VARIANTS.values()],
    ids=lambda path: path.name,
)
@pytest.mark.parametrize("published_default", PUBLISHED_DEFAULTS)
def test_compose_ships_no_published_credential(
    path: Path, published_default: str
) -> None:
    """No compose file may resolve a credential from a value committed here."""
    assert published_default not in _read(path)


@pytest.mark.parametrize(
    "name", ["env.template", "env.prod.template", "docker-compose.template.yml"]
)
@pytest.mark.parametrize("published_default", PUBLISHED_DEFAULTS)
def test_env_templates_ship_no_published_credential(
    name: str, published_default: str
) -> None:
    assert published_default not in _read(COMPOSE_DIR / name)


@pytest.mark.parametrize(
    "name", ["env.template", "env.prod.template"], ids=["default", "prod"]
)
@pytest.mark.parametrize(
    "variable", [*REQUIRED_CREDENTIAL_VARS, *DEFAULT_ONLY_REQUIRED_VARS]
)
def test_env_template_declares_credential_without_a_value(
    name: str, variable: str
) -> None:
    """The env templates name every required credential and assign nothing.

    An operator sees which variables to supply; a copied template cannot carry a
    working credential.
    """
    text = _read(COMPOSE_DIR / name)
    assignments = re.findall(rf"^{variable}=(.*)$", text, flags=re.MULTILINE)
    assert assignments, f"{name} does not declare {variable}"
    for value in assignments:
        assert value.strip() == "", f"{name} assigns a value to {variable}"


def test_prod_env_template_declares_the_production_only_credentials() -> None:
    text = _read(COMPOSE_DIR / "env.prod.template")
    for variable in ("USER_AUTH_SECRET", *PRODUCTION_ONLY_REQUIRED_VARS):
        assignments = re.findall(rf"^{variable}=(.*)$", text, flags=re.MULTILINE)
        assert assignments, f"env.prod.template does not declare {variable}"
        for value in assignments:
            assert value.strip() == ""


def test_no_deployment_artifact_echoes_a_credential_value() -> None:
    """Startup commands must not print credential variables.

    A compose ``command`` runs in a shell, so an ``echo``/``printf`` naming one of
    these variables would put its value in the container log.
    """
    leaky = re.compile(
        r"(?:echo|printf)[^\n]*\$\{?(?:"
        + "|".join((*ALL_CREDENTIAL_VARS, "USER_AUTH_SECRET"))
        + r")\b"
    )
    for path in (TEMPLATE, *GENERATED_VARIANTS.values()):
        assert not leaky.search(_read(path)), f"{path.name} echoes a credential"


# --------------------------------------------------------------------------
# Architecture preservation
# --------------------------------------------------------------------------


@pytest.mark.parametrize("variant", sorted(GENERATED_VARIANTS))
def test_expected_services_are_present(variant: str) -> None:
    services = _load_compose(GENERATED_VARIANTS[variant])["services"]
    missing = [name for name in EXPECTED_SERVICES if name not in services]
    assert not missing, f"{variant} variant lost services: {missing}"


@pytest.mark.parametrize("variant", sorted(GENERATED_VARIANTS))
def test_health_checks_and_dependencies_survive(variant: str) -> None:
    services = _load_compose(GENERATED_VARIANTS[variant])["services"]
    for name in ("api_server", "web_server", "relational_db", "minio"):
        assert "healthcheck" in services[name], f"{name} lost its health check"
    api_dependencies = set(services["api_server"]["depends_on"])
    for name in ("relational_db", "opensearch", "cache", "inference_model_server"):
        assert name in api_dependencies, f"api_server no longer depends on {name}"


@pytest.mark.parametrize("variant", sorted(GENERATED_VARIANTS))
def test_persistent_volumes_survive(variant: str) -> None:
    volumes = _load_compose(GENERATED_VARIANTS[variant])["volumes"]
    for name in (
        "db_volume",
        "opensearch-data",
        "minio_data",
        "model_cache_huggingface",
    ):
        assert name in volumes, f"{variant} variant lost the {name} volume"


def test_supervisor_workers_survive() -> None:
    parser = ConfigParser(strict=False, interpolation=None)
    parser.read_string(_read(REPO_ROOT / "backend" / "supervisord.conf"))
    programs = {
        section.split(":", 1)[1]
        for section in parser.sections()
        if section.startswith("program:")
    }
    missing = [name for name in EXPECTED_SUPERVISOR_PROGRAMS if name not in programs]
    assert not missing, f"supervisord.conf lost workers: {missing}"


# --------------------------------------------------------------------------
# Edition and privacy invariants
# --------------------------------------------------------------------------


def test_paid_enterprise_flag_stays_off() -> None:
    """Turning this on without a license gates the whole application.

    The env template ships it false and nothing in the compose files overrides
    it, so a default deployment resolves to the community tier with the shared
    implementation tree still loaded.
    """
    assert "ENABLE_PAID_ENTERPRISE_EDITION_FEATURES=false" in _read(
        COMPOSE_DIR / "env.template"
    )
    for path in (TEMPLATE, *GENERATED_VARIANTS.values()):
        text = _read(path)
        assert "ENABLE_PAID_ENTERPRISE_EDITION_FEATURES" not in text, (
            f"{path.name} must not set the paid enterprise flag"
        )


def test_license_enforcement_is_left_at_its_default() -> None:
    """The default keeps the shared implementation tree loaded.

    That tree computes group-aware document access, so no deployment artifact may
    switch it off as a shortcut.
    """
    paths = [TEMPLATE, *GENERATED_VARIANTS.values()]
    paths += [COMPOSE_DIR / "env.template", COMPOSE_DIR / "env.prod.template"]
    for path in paths:
        for line in _read(path).splitlines():
            stripped = line.strip().lstrip("#").strip()
            assert not stripped.startswith("LICENSE_ENFORCEMENT_ENABLED="), (
                f"{path.name} sets LICENSE_ENFORCEMENT_ENABLED"
            )


def test_multi_tenant_provisioning_stays_off() -> None:
    """TON is single-tenant; no owned compose variant may enable provisioning."""
    for path in (TEMPLATE, *GENERATED_VARIANTS.values()):
        text = _read(path)
        assert "MULTI_TENANT=true" not in text
        assert "CONTROL_PLANE_API_BASE_URL" not in text


def test_telemetry_defaults_are_not_re_enabled() -> None:
    """Plan 002 turned external analytics off. Deployment must not undo it."""
    for path in (
        TEMPLATE,
        *GENERATED_VARIANTS.values(),
        COMPOSE_DIR / "env.template",
        COMPOSE_DIR / "env.prod.template",
    ):
        for line in _read(path).splitlines():
            stripped = line.strip().lstrip("#").strip()
            assert not stripped.startswith("DISABLE_TELEMETRY=false")
            assert not stripped.startswith("POSTHOG_API_KEY=")
            assert not stripped.startswith("NEXT_PUBLIC_POSTHOG_KEY=")
            assert not stripped.startswith("HUBSPOT_TRACKING_URL=")


# --------------------------------------------------------------------------
# Generated artifact synchronization
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "docker-compose.yml",
        "docker-compose.prod.yml",
        "env.template",
        "env.prod.template",
    ],
)
def test_embedded_cli_copy_matches_the_deployment_source(name: str) -> None:
    """The CLI ships byte-identical copies; `ods generate-compose --write` syncs them."""
    assert (EMBEDDED_DIR / name).read_bytes() == (COMPOSE_DIR / name).read_bytes(), (
        f"embedded {name} is stale: run `ods generate-compose --write`"
    )


@pytest.mark.parametrize("variant", sorted(GENERATED_VARIANTS))
def test_generated_files_declare_their_source(variant: str) -> None:
    """A generated file says so, so an editor is pointed at the template."""
    header = _read(GENERATED_VARIANTS[variant])[:600]
    assert "THIS FILE IS GENERATED - DO NOT EDIT DIRECTLY" in header
    assert "docker-compose.template.yml" in header


@pytest.mark.parametrize("variant", sorted(GENERATED_VARIANTS))
def test_generated_files_carry_no_template_directives(variant: str) -> None:
    for line in _read(GENERATED_VARIANTS[variant]).splitlines():
        assert not line.lstrip().startswith("#!"), f"{variant} leaked a directive"
