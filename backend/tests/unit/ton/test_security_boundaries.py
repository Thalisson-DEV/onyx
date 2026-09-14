import io
import json
import zipfile
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from celery import Celery
from fastapi import UploadFile

from ee.onyx.utils import telemetry as ee_telemetry
from onyx.background.celery.apps import app_base
from onyx.server.documents import connector
from onyx.server.features.projects import projects_file_utils
from onyx.server.query_and_chat import chat_backend
from onyx.server.query_and_chat.placement import Placement
from onyx.tools import tool_runner
from onyx.tools.models import ToolCallException, ToolCallKickoff
from onyx.tracing.framework import create
from onyx.tracing.framework.provider import DefaultTraceProvider
from onyx.tracing.framework.setup import get_trace_provider, set_trace_provider
from onyx.tracing.framework.span_data import GenerationSpanData
from onyx.tracing.framework.traces import TraceContentMode
from onyx.utils import telemetry
from shared_configs.contextvars import CURRENT_TENANT_ID_CONTEXTVAR


class _NonSeekableFile(io.BytesIO):
    def tell(self) -> int:
        raise OSError("tell is not supported")

    def seek(self, *_args: object, **_kwargs: object) -> int:
        raise OSError("seek is not supported")


class _TenantTask(app_base.TenantAwareTask):
    name = "ton.security-test"

    def run(self, *args: object, **kwargs: object) -> str:
        del args, kwargs
        return CURRENT_TENANT_ID_CONTEXTVAR.get() or ""


def _tenant_task() -> _TenantTask:
    celery_app = Celery("ton-security-tests")
    return celery_app.register_task(_TenantTask())


def _zip_file(entries: list[tuple[str, bytes]]) -> zipfile.ZipFile:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        for name, content in entries:
            output.writestr(name, content)
    archive.seek(0)
    return zipfile.ZipFile(archive)


def test_ton_task_rejects_missing_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_base, "TON_WEB_ONLY", True)

    with pytest.raises(ValueError, match="tenant_id"):
        _tenant_task()()


def test_ton_task_rejects_empty_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_base, "TON_WEB_ONLY", True)

    with pytest.raises(ValueError, match="tenant_id"):
        _tenant_task()(tenant_id="")


def test_ton_task_rejects_mismatched_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_base, "TON_WEB_ONLY", True)
    task = _tenant_task()
    task.push_request(headers={app_base.TENANT_ID_HEADER: "tenant-a"})
    try:
        with pytest.raises(ValueError, match="tenant context"):
            task(tenant_id="tenant-b")
    finally:
        task.pop_request()


def test_default_task_keeps_legacy_tenant_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_base, "TON_WEB_ONLY", False)

    assert _tenant_task()() == app_base.POSTGRES_DEFAULT_SCHEMA


def test_task_publisher_stamps_tenant_header() -> None:
    headers: dict[str, Any] = {}

    app_base.on_before_task_publish(
        headers=headers,
        body=((), {"tenant_id": "tenant-a"}, None),
    )

    assert headers[app_base.TENANT_ID_HEADER] == "tenant-a"
    assert isinstance(headers["enqueued_at"], float)


def test_ton_postrun_does_not_use_default_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = MagicMock()
    monkeypatch.setattr(app_base, "TON_WEB_ONLY", True)
    monkeypatch.setattr(app_base, "get_redis_client", redis_client)
    task = MagicMock()
    task.name = "document_sync"

    app_base.on_task_postrun(
        task=task,
        task_id=f"{app_base.DOCUMENT_SYNC_PREFIX}123",
        kwargs={},
        state="SUCCESS",
    )

    redis_client.assert_not_called()


def test_ton_revoked_task_does_not_use_default_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = MagicMock()
    monkeypatch.setattr(app_base, "TON_WEB_ONLY", True)
    monkeypatch.setattr(app_base, "get_redis_client", redis_client)
    request = SimpleNamespace(
        id=f"{app_base.DOCUMENT_SYNC_PREFIX}123",
        kwargs={},
    )

    app_base.on_task_revoked(request=request)

    redis_client.assert_not_called()


def test_ton_task_reset_clears_tenant_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_base, "TON_WEB_ONLY", True)
    token = CURRENT_TENANT_ID_CONTEXTVAR.set("tenant-a")
    try:
        app_base.reset_tenant_id()
        assert CURRENT_TENANT_ID_CONTEXTVAR.get() is None
    finally:
        CURRENT_TENANT_ID_CONTEXTVAR.reset(token)


def test_zip_rejects_excessive_members(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(connector, "MAX_ZIP_ENTRIES", 1)
    with _zip_file([("one.txt", b"1"), ("two.txt", b"2")]) as archive:
        with pytest.raises(Exception, match="too many files"):
            connector.validate_zip_archive(archive)


def test_zip_rejects_oversized_expansion_before_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(connector, "MAX_ZIP_EXPANDED_SIZE_BYTES", 3)
    with _zip_file([("large.txt", b"1234")]) as archive:
        with pytest.raises(Exception, match="expanded size"):
            connector.validate_zip_archive(archive)


def test_zip_rejects_oversized_member(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(connector, "MAX_ZIP_MEMBER_SIZE_BYTES", 3)
    with _zip_file([("large.txt", b"1234")]) as archive:
        with pytest.raises(Exception, match="member exceeds"):
            connector.validate_zip_archive(archive)


def test_zip_rejects_excessive_compression_ratio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(connector, "MAX_ZIP_COMPRESSION_RATIO", 1)
    with _zip_file([("compressed.txt", b"a" * 1000)]) as archive:
        with pytest.raises(Exception, match="compression ratio"):
            connector.validate_zip_archive(archive)


def test_zip_rejects_long_filename(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(connector, "MAX_ZIP_FILENAME_LENGTH", 8)
    with _zip_file([("too-long.txt", b"x")]) as archive:
        with pytest.raises(Exception, match="unsafe path"):
            connector.validate_zip_archive(archive)


def test_zip_bounded_reader_enforces_actual_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(connector, "MAX_ZIP_MEMBER_SIZE_BYTES", 3)
    with _zip_file([("large.txt", b"1234")]) as archive:
        member = archive.infolist()[0]
        with pytest.raises(Exception, match="expanded size"):
            connector._read_bounded_zip_member(archive, member, 10)


def test_malformed_zip_is_rejected_as_bad_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(connector, "get_default_file_store", MagicMock())
    upload = UploadFile(filename="broken.zip", file=io.BytesIO(b"not a zip"))

    with pytest.raises(Exception) as exc_info:
        connector.upload_files([upload])

    assert getattr(exc_info.value, "status_code", None) == 400


def test_zip_rejects_unsafe_name_and_depth() -> None:
    with _zip_file([("../secret.txt", b"secret")]) as archive:
        with pytest.raises(Exception, match="unsafe path"):
            connector.validate_zip_archive(archive)

    deep_name = "/".join(["level"] * (connector.MAX_ZIP_PATH_DEPTH + 1))
    with _zip_file([(f"{deep_name}/file.txt", b"x")]) as archive:
        with pytest.raises(Exception, match="path depth"):
            connector.validate_zip_archive(archive)


def test_unknown_size_upload_is_counted_and_buffered() -> None:
    upload = UploadFile(
        filename="unknown.txt",
        file=_NonSeekableFile(b"1234"),
        size=None,
    )

    assert projects_file_utils.is_upload_too_large(upload, max_bytes=3)
    assert upload.file.read(4) == b"1234"


def test_unknown_size_upload_under_limit_remains_readable() -> None:
    upload = UploadFile(
        filename="unknown.txt",
        file=_NonSeekableFile(b"123"),
        size=None,
    )

    assert not projects_file_utils.is_upload_too_large(upload, max_bytes=3)
    assert upload.file.read() == b"123"


def test_stream_error_is_stable_and_keeps_request_id() -> None:
    token = chat_backend.ONYX_REQUEST_ID_CONTEXTVAR.set("API:abc123")
    try:
        payload = json.loads(chat_backend.get_public_stream_error())
    finally:
        chat_backend.ONYX_REQUEST_ID_CONTEXTVAR.reset(token)

    assert payload == {
        "error": "An internal error occurred.",
        "error_code": "INTERNAL_ERROR",
        "request_id": "API:abc123",
    }


def test_ton_trace_defaults_to_metadata_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(create, "TON_WEB_ONLY", True)
    monkeypatch.setattr(create, "TON_TRACE_CONTENT_MODE", "metadata")

    trace = create.trace("ton-security-test", disabled=True)

    assert trace.content_mode == TraceContentMode.METADATA_ONLY


def test_metadata_trace_removes_model_content_and_private_config() -> None:
    provider = DefaultTraceProvider()

    with provider.create_trace(
        "ton-model-trace",
        content_mode=TraceContentMode.METADATA_ONLY,
    ):
        span = provider.create_span(
            GenerationSpanData(
                input=[{"role": "user", "content": "secret prompt"}],
                output=[{"role": "assistant", "content": "secret response"}],
                reasoning="secret reasoning",
                tools=[{"name": "secret-tool"}],
                request_params={"api_key": "secret-key"},
                model="test-model",
                model_config={
                    "model_provider": "test-provider",
                    "flow": "chat",
                    "api_key": "secret-key",
                    "base_url": "https://private.example.com",
                },
                usage={"input_tokens": 4, "output_tokens": 2},
            )
        )

    exported = span.span_data.export()
    assert exported["input"] is None
    assert exported["output"] is None
    assert exported["reasoning"] is None
    assert exported["tools"] is None
    assert exported["request_params"] is None
    assert exported["model_config"] == {
        "model_provider": "test-provider",
        "flow": "chat",
    }
    assert exported["usage"] == {"input_tokens": 4, "output_tokens": 2}


def test_metadata_trace_removes_tool_arguments_and_error_content() -> None:
    original_provider = get_trace_provider()
    provider = DefaultTraceProvider()
    processor = MagicMock()
    provider.register_processor(processor)
    set_trace_provider(provider)
    tool = MagicMock()
    tool.name = "sensitive_tool"
    tool.run.side_effect = ToolCallException(
        "secret provider error",
        "secret LLM error",
    )
    tool_call = ToolCallKickoff(
        tool_call_id="call-1",
        tool_name=tool.name,
        tool_args={"query": "secret payroll"},
        placement=Placement(turn_index=0),
    )

    try:
        with provider.create_trace(
            "ton-tool-trace",
            content_mode=TraceContentMode.METADATA_ONLY,
        ):
            tool_runner._safe_run_single_tool(tool, tool_call, None)
    finally:
        set_trace_provider(original_provider)

    span = processor.on_span_end.call_args.args[0]
    serialized = json.dumps(span.export())
    assert span.span_data.input is None
    assert span.span_data.output is None
    assert "secret payroll" not in serialized
    assert "secret provider error" not in serialized
    assert "secret LLM error" not in serialized


def test_ton_external_telemetry_is_off_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outbound = MagicMock()
    monkeypatch.setattr(telemetry, "TON_WEB_ONLY", True)
    monkeypatch.setattr(telemetry, "TON_EXTERNAL_TELEMETRY_MODE", "off")
    monkeypatch.setattr(telemetry.requests, "post", outbound)

    delivered = telemetry.optional_telemetry(
        telemetry.RecordType.USAGE,
        {"prompt": "sensitive payroll data"},
        blocking=True,
    )

    assert delivered is False
    outbound.assert_not_called()


def test_ton_enterprise_telemetry_is_off_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    posthog = MagicMock()
    monkeypatch.setattr(ee_telemetry, "TON_WEB_ONLY", True)
    monkeypatch.setattr(ee_telemetry, "TON_EXTERNAL_TELEMETRY_MODE", "off")
    monkeypatch.setattr(ee_telemetry, "posthog", posthog)

    ee_telemetry.event_telemetry(
        "user@example.com",
        "secret_event",
        {"prompt": "secret payroll data"},
    )
    ee_telemetry.identify_user(
        "user@example.com",
        {"email": "user@example.com"},
    )

    posthog.capture.assert_not_called()
    posthog.identify.assert_not_called()


def test_ton_metadata_telemetry_uses_allowlisted_fields_only() -> None:
    assert telemetry.redact_ton_telemetry_data(
        {
            "status": "success",
            "latency": "0.2",
            "prompt": "sensitive payroll data",
            "response": "sensitive contract data",
        }
    ) == {"status": "success", "latency": "0.2"}


def test_ton_metadata_telemetry_sends_only_allowlisted_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = MagicMock(ok=True)
    outbound = MagicMock(return_value=response)
    monkeypatch.setattr(telemetry, "TON_WEB_ONLY", True)
    monkeypatch.setattr(telemetry, "TON_EXTERNAL_TELEMETRY_MODE", "metadata")
    monkeypatch.setattr(telemetry, "DISABLE_TELEMETRY", False)
    monkeypatch.setattr(telemetry, "MULTI_TENANT", False)
    monkeypatch.setattr(telemetry, "get_or_generate_uuid", lambda: "instance-id")
    monkeypatch.setattr(telemetry.requests, "post", outbound)

    delivered = telemetry.optional_telemetry(
        telemetry.RecordType.USAGE,
        {
            "status": "success",
            "latency": "0.2",
            "prompt": "secret payroll data",
        },
        user_id="user@example.com",
        blocking=True,
    )

    assert delivered is True
    payload = outbound.call_args.kwargs["json"]
    assert payload["data"] == {"status": "success", "latency": "0.2"}
    assert payload["user_id"] is None
    assert "instance_domain" not in payload
    assert "secret" not in json.dumps(payload)
