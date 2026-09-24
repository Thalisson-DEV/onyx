import logging
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from onyx.ton.zeev.client import (
    ZeevAuthenticationError,
    ZeevClient,
    ZeevConfig,
    ZeevConfigurationError,
    ZeevPermissionError,
    ZeevProtocolError,
    ZeevRateLimitError,
    ZeevReadOnlyViolation,
    ZeevUnavailableError,
    _assert_read_only,
    _Operation,
)
from onyx.ton.zeev.models import ZeevHealthState, ZeevInstanceQuery


def _client(
    handler: httpx.MockTransport,
    *,
    token: str | None = "example-token",
    password: str | None = None,
) -> ZeevClient:
    config = ZeevConfig(
        enabled=True,
        base_url="https://nucleo.zeev.it",
        username="local-user" if password else None,
        password=password,
        token=token,
    )
    return ZeevClient(
        config,
        httpx.Client(base_url=config.base_url, transport=handler),
    )


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE", "POST"])
def test_mutation_method_is_blocked_before_network(method: str) -> None:
    calls: list[httpx.Request] = []
    client = _client(
        httpx.MockTransport(
            lambda request: calls.append(request) or httpx.Response(200)
        )
    )
    with pytest.raises(ZeevReadOnlyViolation):
        _assert_read_only(method, "/api/2/instances", _Operation.FLOWS)
    assert calls == []
    client.close()


@pytest.mark.parametrize(
    "path",
    [
        "/api/2/instances",
        "/api/2/flows/import",
        "/api/2/flows/1/design/form/../../instances",
        "/api/2/flows/0/design/form",
        "https://another-host/api/2/requests/flows",
    ],
)
def test_unknown_path_is_blocked_before_network(path: str) -> None:
    calls: list[httpx.Request] = []
    client = _client(
        httpx.MockTransport(
            lambda request: calls.append(request) or httpx.Response(200)
        )
    )
    with pytest.raises(ZeevReadOnlyViolation):
        client._send(_Operation.FLOWS, path=path)
    assert calls == []


def test_mutation_body_is_blocked_before_network() -> None:
    calls: list[httpx.Request] = []
    client = _client(
        httpx.MockTransport(
            lambda request: calls.append(request) or httpx.Response(200)
        )
    )
    with pytest.raises(ZeevReadOnlyViolation):
        client._send(_Operation.FLOWS, json_body={"danger": True})
    assert calls == []


def test_unbounded_report_is_blocked_before_network() -> None:
    calls: list[httpx.Request] = []
    client = _client(
        httpx.MockTransport(
            lambda request: calls.append(request) or httpx.Response(200)
        )
    )
    with pytest.raises(ZeevReadOnlyViolation):
        client._send(_Operation.INSTANCES, params={"pageNumber": 1})
    with pytest.raises(ZeevReadOnlyViolation):
        client._send(_Operation.INSTANCES_POST, json_body={"recordsPerPage": 100})
    assert calls == []


def test_config_validation_and_secret_repr() -> None:
    with pytest.raises(ZeevConfigurationError):
        ZeevConfig(enabled=True, base_url="http://nucleo.zeev.it", token="secret")
    config = ZeevConfig(
        enabled=True,
        base_url="https://nucleo.zeev.it",
        username="hidden-user",
        password="hidden-password",
        token="hidden-token",
    )
    representation = repr(config)
    assert "hidden-user" not in representation
    assert "hidden-password" not in representation
    assert "hidden-token" not in representation


def test_login_cache_refresh_and_redacted_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    calls: list[tuple[str, str]] = []
    issued = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal issued
        calls.append((request.method, request.url.path))
        if request.method == "POST":
            issued += 1
            return httpx.Response(
                200, json={"temporaryToken": f"private-token-{issued}"}
            )
        if request.headers["Authorization"] == "Bearer private-token-1":
            return httpx.Response(401, json={"error": "bad"})
        return httpx.Response(200, json={"userId": 1})

    client = _client(
        httpx.MockTransport(handler), token=None, password="private-password"
    )
    with caplog.at_level(logging.INFO):
        client.authenticate()
        assert client.health_check().state is ZeevHealthState.AVAILABLE
    assert calls == [
        ("POST", "/api/2/tokens"),
        ("GET", "/api/2/tokens"),
        ("POST", "/api/2/tokens"),
        ("GET", "/api/2/tokens"),
    ]
    assert "private-token" not in caplog.text
    assert "private-password" not in caplog.text
    assert "Authorization" not in caplog.text


def test_static_token_takes_priority() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        assert request.headers["Authorization"] == "Bearer configured-token"
        return httpx.Response(200, json={"userId": 1})

    client = ZeevClient(
        ZeevConfig(
            enabled=True,
            base_url="https://nucleo.zeev.it",
            username="user",
            password="password",
            token="configured-token",
        ),
        httpx.Client(
            base_url="https://nucleo.zeev.it", transport=httpx.MockTransport(handler)
        ),
    )
    assert client.health_check().state is ZeevHealthState.AVAILABLE
    assert calls == ["GET"]


def test_401_refreshes_only_once() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if request.method == "POST":
            return httpx.Response(200, json={"temporaryToken": "token"})
        return httpx.Response(401, json={})

    client = _client(httpx.MockTransport(handler), token=None, password="password")
    with pytest.raises(ZeevAuthenticationError):
        client.list_flows()
    assert calls == ["POST", "GET", "POST", "GET"]


def test_flow_form_and_task_parsing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/2/requests/flows":
            return httpx.Response(
                200, json=[{"id": 7, "name": "Operations", "deploy": True}]
            )
        if request.url.path.endswith("/design/form"):
            return httpx.Response(
                200,
                json=[
                    {
                        "fieldId": 12,
                        "name": "field_one",
                        "label": "Field one",
                        "typeName": "Text",
                        "required": True,
                        "attributes": [],
                    }
                ],
            )
        return httpx.Response(
            200,
            json={
                "id": 9,
                "active": True,
                "flow": {"id": 7},
                "instanceTasks": [
                    {"id": 2, "task": {"name": "Review"}, "active": True}
                ],
            },
        )

    client = _client(httpx.MockTransport(handler))
    assert client.list_flows()[0].external_id == 7
    assert client.get_flow_form_fields(7)[0].external_id == 12
    instance = client.get_instance(9)
    assert instance.flow_id == 7
    assert instance.tasks[0].name == "Review"


def test_bounded_get_and_read_only_post_pagination() -> None:
    calls: list[tuple[str, int]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            page = int(__import__("json").loads(request.content)["pageNumber"])
        else:
            page = int(request.url.params["pageNumber"])
        calls.append((request.method, page))
        return httpx.Response(200, json=[{"id": 3}, {"id": 4}])

    client = _client(httpx.MockTransport(handler))
    end = datetime.now(timezone.utc)
    query = ZeevInstanceQuery(
        start=end - timedelta(hours=1), end=end, page_size=2, max_pages=3
    )
    assert len(client.query_instances(query)) == 2
    assert len(client.query_instances(query, use_post=True)) == 2
    assert calls == [("GET", 1), ("GET", 2), ("POST", 1), ("POST", 2)]
    with pytest.raises(ValueError):
        ZeevInstanceQuery(start=end - timedelta(days=8), end=end)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, ZeevAuthenticationError),
        (403, ZeevPermissionError),
        (404, ZeevProtocolError),
        (429, ZeevRateLimitError),
        (503, ZeevUnavailableError),
    ],
)
def test_error_mapping_and_bounded_retries(
    status: int, expected: type[Exception], monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status, headers={"Retry-After": "0"}, json={})

    monkeypatch.setattr("onyx.ton.zeev.client.time.sleep", lambda _delay: None)
    client = _client(httpx.MockTransport(handler))
    with pytest.raises(expected):
        client.list_flows()
    assert calls == (3 if status in (429, 503) else 1)


def test_timeout_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectTimeout("timeout", request=request)

    monkeypatch.setattr("onyx.ton.zeev.client.time.sleep", lambda _delay: None)
    client = _client(httpx.MockTransport(handler))
    with pytest.raises(ZeevUnavailableError):
        client.list_flows()
    assert calls == 3


def test_retry_after_is_bounded() -> None:
    assert ZeevClient._backoff(0, "2") == 2
    assert ZeevClient._backoff(0, "999") == 30


def test_health_disabled_and_unconfigured() -> None:
    disabled = ZeevClient(ZeevConfig(enabled=False, base_url="https://nucleo.zeev.it"))
    assert disabled.health_check().state is ZeevHealthState.DISABLED
    disabled.close()
    unconfigured = ZeevClient(
        ZeevConfig(enabled=True, base_url="https://nucleo.zeev.it")
    )
    assert unconfigured.health_check().state is ZeevHealthState.UNCONFIGURED
    unconfigured.close()
