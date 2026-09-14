from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def _read(relative_path: str) -> str:
    return (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")


def test_plan_002_backend_boundaries_are_wired() -> None:
    task_source = _read("backend/onyx/background/celery/apps/app_base.py")
    upload_source = _read(
        "backend/onyx/server/features/projects/projects_file_utils.py"
    )
    zip_source = _read("backend/onyx/server/documents/connector.py")
    stream_source = _read("backend/onyx/server/query_and_chat/chat_backend.py")
    trace_source = _read("backend/onyx/tracing/framework/create.py")
    telemetry_source = _read("backend/onyx/utils/telemetry.py")

    assert "TON task requires tenant_id" in task_source
    assert "SpooledTemporaryFile" in upload_source
    assert "validate_zip_archive" in zip_source
    assert "get_public_stream_error" in stream_source
    assert "TON_TRACE_CONTENT_MODE" in trace_source
    assert "redact_ton_telemetry_data" in telemetry_source


def test_plan_002_does_not_add_domain_schema_or_migrations() -> None:
    models = _read("backend/onyx/db/models.py")
    for model_name in ("Finding", "Occurrence", "RuleVersion", "AnalysisRun"):
        assert f"class {model_name}(" not in models
