from datetime import datetime

import httpx
import pytest

from onyx.ton.zeev import catalog_cli
from onyx.ton.zeev.catalog import (
    ZeevCatalogService,
    candidate_areas,
    profile_structure,
    source_field_kind,
)
from onyx.ton.zeev.client import (
    ZeevClient,
    ZeevConfig,
    ZeevReadOnlyViolation,
    _Operation,
)
from onyx.ton.zeev.models import (
    ZeevAttachmentReadState,
    ZeevCapabilityState,
    ZeevFieldKind,
    ZeevSchemaState,
    ZeevSourceCatalog,
)


def _client(handler: httpx.MockTransport, calls: list[tuple[str, str]]) -> ZeevClient:
    return ZeevClient(
        ZeevConfig(enabled=True, base_url="https://nucleo.zeev.it", token="test-token"),
        httpx.Client(base_url="https://nucleo.zeev.it", transport=handler),
        audit_call=lambda method, path: calls.append((method, path)),
    )


def test_catalog_unions_flows_and_keeps_values_out() -> None:
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/2/requests/flows":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 3,
                        "name": "Solicitação de Compra",
                        "uid": "stable-3",
                        "version": 4,
                        "deploy": True,
                        "teams": [{"id": 9, "name": "Private Team"}],
                    },
                    {"id": 1, "name": "Chamados de TI"},
                ],
            )
        if path == "/api/2/flows/edit":
            return httpx.Response(
                200,
                json=[
                    {
                        "flowId": 2,
                        "flowName": "Contratos",
                        "flowVersion": 2,
                        "active": False,
                    },
                    {
                        "flowId": 3,
                        "flowName": "Solicitação de Compra",
                        "flowUid": "stable-3",
                        "flowVersion": 4,
                        "active": True,
                    },
                ],
            )
        if path == "/api/2/requests/services":
            return httpx.Response(200, json=[])
        if path.endswith("/design/elements"):
            users: object = (
                "private-role-expression"
                if path == "/api/2/flows/2/design/elements"
                else [{"name": "Private Person"}]
            )
            return httpx.Response(
                200,
                json=[
                    {
                        "taskId": 5,
                        "title": "Review",
                        "type": "Tarefa Humana",
                        "users": users,
                        "page": 1,
                    }
                ],
            )
        if path == "/api/2/flows/1/design/form":
            return httpx.Response(403)
        if path == "/api/2/flows/2/design/form":
            return httpx.Response(
                200,
                json=[
                    {
                        "fieldId": 22,
                        "name": "rows",
                        "label": "Itens",
                        "typeName": "Tabela",
                        "groupName": "Contrato",
                        "rowOrder": 2,
                    },
                    {
                        "fieldId": 21,
                        "name": "odd",
                        "label": "Secreto",
                        "typeName": "Unknown Widget",
                        "rowOrder": 1,
                    },
                ],
            )
        if path == "/api/2/flows/3/design/form":
            return httpx.Response(
                200,
                json=[
                    {
                        "fieldId": 31,
                        "name": "file",
                        "label": "Anexo",
                        "typeName": "Arquivo",
                        "actionScript": "private-script-value",
                    },
                    {
                        "fieldId": 32,
                        "name": "choice",
                        "label": "Fornecedor",
                        "typeName": "Lista de seleção",
                        "attributes": ["A", "B"],
                    },
                ],
            )
        if path == "/api/2/instances/report":
            assert request.url.params["pageNumber"] == "1"
            assert request.url.params["recordsPerPage"] == "5"
            start = datetime.fromisoformat(request.url.params["startDateIntervalBegin"])
            end = datetime.fromisoformat(request.url.params["startDateIntervalEnd"])
            assert (end - start).total_seconds() == 86400
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 9,
                        "flow": {"id": 3},
                        "requester": {
                            "id": 7,
                            "team": {"id": 8},
                            "position": {"id": 10},
                            "name": "Private Person",
                        },
                        "formFields": [
                            {"name": "salary", "value": "private-salary-value"}
                        ],
                        "instanceTasks": [
                            {
                                "id": 11,
                                "active": False,
                                "startDateTime": "2026-09-23T00:00:00Z",
                                "task": {"name": "Review"},
                                "assignees": [
                                    {"team": {"id": 8}, "name": "Private Person"}
                                ],
                            }
                        ],
                    }
                ],
            )
        if path == "/api/2/assignments":
            assert request.url.params["recordsPerPage"] == "5"
            return httpx.Response(200, json=[])
        if path == "/api/2/instances/9":
            assert request.url.params.get_list("formFieldNames") == ["file"]
            return httpx.Response(
                200,
                json={
                    "id": 9,
                    "flow": {"id": 3},
                    "requester": {
                        "id": 7,
                        "team": {"id": 8},
                        "position": {"id": 10},
                        "name": "Private Person",
                    },
                    "formFields": [
                        {
                            "name": "file",
                            "value": "private-file-reference",
                            "openUrl": None,
                        }
                    ],
                    "instanceTasks": [
                        {
                            "id": 11,
                            "active": False,
                            "startDateTime": "2026-09-23T00:00:00Z",
                            "task": {"name": "Review"},
                            "assignees": [
                                {"team": {"id": 8}, "name": "Private Person"}
                            ],
                        }
                    ],
                },
            )
        if path in {"/api/2/users/7", "/api/2/teams/8", "/api/2/positions/10"}:
            return httpx.Response(200, json={"id": 7, "name": "Private Person"})
        raise AssertionError(path)

    client = _client(httpx.MockTransport(handler), calls)
    catalog = ZeevCatalogService(client, interval_seconds=0).discover()
    assert [flow.external_id for flow in catalog.flows] == [1, 2, 3]
    assert [(flow.startable, flow.editable) for flow in catalog.flows] == [
        (True, False),
        (False, True),
        (True, True),
    ]
    assert catalog.flows[2].uid == "stable-3"
    assert catalog.flows[2].version == 4
    assert catalog.flows[2].startable_team_ids == (9,)
    assert catalog.flows[0].schema_state is ZeevSchemaState.PERMISSION_DENIED
    assert catalog.flows[1].schema is not None
    assert [field.external_id for field in catalog.flows[1].schema.fields] == [21, 22]
    assert catalog.flows[1].schema.fields[0].kind is ZeevFieldKind.UNKNOWN
    assert catalog.flows[1].schema.fields[0].zeev_type == "Unknown Widget"
    assert catalog.flows[1].schema.fields[1].repeating is True
    assert catalog.field_count == 4
    assert catalog.design_element_count == 3
    assert catalog.flows[2].design_elements[0].user_count == 1
    assert catalog.flows[2].design_elements[0].user_representation == "array"
    assert catalog.flows[1].design_elements[0].user_representation == "string"
    assert catalog.attachment_read is ZeevAttachmentReadState.REFERENCE_ONLY
    assert catalog.instance_sample_count == 1
    assert catalog.task_sample_count == 1
    assert [(warning.external_id, warning.state) for warning in catalog.warnings] == [
        (1, "PERMISSION_DENIED")
    ]
    capabilities = {item.name: item.state for item in catalog.capabilities}
    assert capabilities["task_team"] is ZeevCapabilityState.LIVE_VALIDATED
    assert capabilities["users"] is ZeevCapabilityState.LIVE_VALIDATED
    assert capabilities["teams"] is ZeevCapabilityState.LIVE_VALIDATED
    assert capabilities["roles"] is ZeevCapabilityState.LIVE_VALIDATED
    assert capabilities["attachment_download"] is ZeevCapabilityState.NOT_FOUND
    safe_output = repr(catalog)
    assert "private-" not in safe_output
    assert "private-script-value" not in safe_output
    assert "private-file-reference" not in safe_output
    assert "private-role-expression" not in safe_output
    assert "Private Team" not in safe_output
    assert ("GET", "/api/2/flows/{flowid}/design/form") in calls
    assert not any(method in {"PUT", "PATCH", "DELETE"} for method, _ in calls)
    client.close()


def test_candidate_classification_uses_only_names_and_labels() -> None:
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/2/requests/flows":
            return httpx.Response(200, json=[{"id": 1, "name": "Processo Geral"}])
        if request.url.path == "/api/2/flows/edit":
            return httpx.Response(200, json=[])
        if request.url.path == "/api/2/requests/services":
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/design/elements"):
            return httpx.Response(200, json=[])
        return httpx.Response(
            200,
            json=[
                {
                    "fieldId": 1,
                    "name": "other",
                    "label": "Contrato",
                    "typeName": "Texto",
                    "actionScript": "compra financeira",
                }
            ],
        )

    client = _client(httpx.MockTransport(handler), calls)
    catalog = ZeevCatalogService(client, interval_seconds=0).discover(
        sample_instances=False
    )
    areas = candidate_areas(catalog.flows[0])
    assert [candidate.area for candidate in areas] == ["Contratos"]
    assert "Financeiro" not in repr(areas)
    assert "Compras" not in repr(areas)
    client.close()


def test_structure_profile_discards_nested_values() -> None:
    profile = profile_structure(
        [
            {
                "requester": {"name": "Private Person"},
                "tasks": [{"value": "secret-a"}, {"value": None}],
            },
            {"requester": None, "tasks": []},
        ]
    )
    by_path = {field.path: field for field in profile}
    assert by_path["requester"].null_count == 1
    assert by_path["tasks"].min_items == 0
    assert by_path["tasks"].max_items == 2
    assert by_path["tasks[].value"].null_count == 1
    assert "Private Person" not in repr(profile)
    assert "secret-a" not in repr(profile)


def test_rate_limit_stops_schema_expansion(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr("onyx.ton.zeev.client.time.sleep", lambda _delay: None)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/2/requests/flows":
            return httpx.Response(
                200, json=[{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
            )
        if request.url.path == "/api/2/flows/edit":
            return httpx.Response(200, json=[])
        if request.url.path == "/api/2/requests/services":
            return httpx.Response(200, json=[])
        return httpx.Response(429, headers={"Retry-After": "0"}, json={})

    client = _client(httpx.MockTransport(handler), calls)
    catalog = ZeevCatalogService(client, interval_seconds=0).discover()
    assert len(catalog.flows) == 2
    assert all(
        flow.schema_state is ZeevSchemaState.SCHEMA_UNAVAILABLE
        for flow in catalog.flows
    )
    assert calls.count(("GET", "/api/2/flows/{flowid}/design/form")) == 3
    assert ("GET", "/api/2/instances/report") not in calls
    assert any(warning.state == "RATE_LIMITED" for warning in catalog.warnings)
    client.close()


def test_protocol_error_keeps_other_flow_schemas() -> None:
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/2/requests/flows":
            return httpx.Response(
                200, json=[{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
            )
        if request.url.path in {"/api/2/flows/edit", "/api/2/requests/services"}:
            return httpx.Response(200, json=[])
        if request.url.path == "/api/2/flows/1/design/form":
            return httpx.Response(404, json={})
        if request.url.path.endswith("/design/elements"):
            return httpx.Response(200, json=[])
        return httpx.Response(
            200, json=[{"fieldId": 1, "name": "code", "typeName": "Texto"}]
        )

    client = _client(httpx.MockTransport(handler), calls)
    catalog = ZeevCatalogService(client, interval_seconds=0).discover(
        sample_instances=False
    )
    assert catalog.flows[0].schema_state is ZeevSchemaState.PROTOCOL_ERROR
    assert catalog.flows[1].schema_state is ZeevSchemaState.AVAILABLE
    assert catalog.field_count == 1
    client.close()


def test_report_rate_limit_returns_partial_catalog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr("onyx.ton.zeev.client.time.sleep", lambda _delay: None)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/2/requests/flows":
            return httpx.Response(200, json=[{"id": 1, "name": "A"}])
        if request.url.path == "/api/2/instances/report":
            return httpx.Response(429, headers={"Retry-After": "0"}, json={})
        return httpx.Response(200, json=[])

    client = _client(httpx.MockTransport(handler), calls)
    catalog = ZeevCatalogService(client, interval_seconds=0).discover()
    assert len(catalog.flows) == 1
    assert catalog.flows[0].schema_state is ZeevSchemaState.AVAILABLE
    assert catalog.instance_sample_count == 0
    assert any(warning.state == "RATE_LIMITED" for warning in catalog.warnings)
    assert ("GET", "/api/2/assignments") not in calls
    capabilities = {item.name: item.state for item in catalog.capabilities}
    assert capabilities["instance_report"] is ZeevCapabilityState.DOCUMENTED
    assert capabilities["pending_tasks"] is ZeevCapabilityState.DOCUMENTED
    client.close()


def test_catalog_paces_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    pauses: list[float] = []
    monkeypatch.setattr("onyx.ton.zeev.catalog.time.sleep", pauses.append)
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/2/requests/flows":
            return httpx.Response(200, json=[{"id": 1, "name": "A"}])
        return httpx.Response(200, json=[])

    client = _client(httpx.MockTransport(handler), calls)
    ZeevCatalogService(client, interval_seconds=0.1).discover(sample_instances=False)
    assert pauses == [0.1, 0.1, 0.1, 0.1]
    client.close()


def test_new_probe_paths_obey_firewall() -> None:
    network: list[httpx.Request] = []
    client = _client(
        httpx.MockTransport(
            lambda request: network.append(request) or httpx.Response(200, json={})
        ),
        calls := [],
    )
    with pytest.raises(ZeevReadOnlyViolation):
        client._send(_Operation.USER, path="/api/2/users/1/account/deactivate")
    with pytest.raises(ValueError):
        client.get_instance(1, form_field_names=("one", "two", "three", "four"))
    assert network == []
    client.probe_user(7)
    assert calls == [("GET", "/api/2/users/{userid}")]
    assert network[0].url.path == "/api/2/users/7"
    client.close()


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Arquivo - Visualizador", ZeevFieldKind.FILE),
        ("Moeda", ZeevFieldKind.NUMBER),
        ("Tabela", ZeevFieldKind.TABLE),
        ("unseen type", ZeevFieldKind.UNKNOWN),
    ],
)
def test_source_field_kind_keeps_unknown(name: str, expected: ZeevFieldKind) -> None:
    assert source_field_kind(name) is expected


def test_catalog_cli_prints_only_safe_summary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    catalog = ZeevSourceCatalog(
        flows=(),
        services=(),
        capabilities=(),
        warnings=(),
        candidates=(),
        instance_structure=(),
        task_structure=(),
        instance_sample_count=0,
        task_sample_count=0,
        attachment_read=ZeevAttachmentReadState.REFERENCE_ONLY,
    )

    class FakeClient:
        def __init__(
            self, _config: ZeevConfig, audit_call: object, audit_status: object
        ) -> None:
            self.audit_call = audit_call
            self.audit_status = audit_status

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args: object) -> None:
            pass

    class FakeService:
        def __init__(self, _client: FakeClient) -> None:
            pass

        def discover(self) -> ZeevSourceCatalog:
            return catalog

    monkeypatch.setattr(
        catalog_cli.ZeevConfig,
        "from_env",
        lambda: ZeevConfig(
            enabled=True, base_url="https://nucleo.zeev.it", token="private-token"
        ),
    )
    monkeypatch.setattr(catalog_cli, "ZeevClient", FakeClient)
    monkeypatch.setattr(catalog_cli, "ZeevCatalogService", FakeService)
    assert catalog_cli.main() == 0
    output = capsys.readouterr().out
    assert "private-token" not in output
    assert "Mutation calls: 0" in output
    assert "Attachments: REFERENCE_ONLY" in output
