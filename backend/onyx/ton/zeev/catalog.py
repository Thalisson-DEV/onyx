"""Value-safe source discovery built on the Zeev read-only client."""

import time
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from onyx.ton.zeev.client import (
    ZeevClient,
    ZeevPermissionError,
    ZeevProtocolError,
    ZeevRateLimitError,
    ZeevUnavailableError,
)
from onyx.ton.zeev.models import (
    ZeevAttachmentReadState,
    ZeevCandidateArea,
    ZeevCapability,
    ZeevCapabilityState,
    ZeevCatalogWarning,
    ZeevDesignElement,
    ZeevFieldKind,
    ZeevFlowCatalogEntry,
    ZeevFormField,
    ZeevFormFieldCatalogEntry,
    ZeevFormSchemaCatalog,
    ZeevInstance,
    ZeevInstanceQuery,
    ZeevSchemaState,
    ZeevServiceCatalogEntry,
    ZeevSourceCatalog,
    ZeevStructureField,
    ZeevTask,
)

_AREA_TERMS: dict[str, tuple[str, ...]] = {
    "Financeiro": ("financeir", "pagamento", "fatura", "nota fiscal", "orcament"),
    "Compras": ("compra", "aquisic", "fornecedor"),
    "Contratos": ("contrato", "juridic", "assinatura"),
    "Frota": ("frota", "veiculo", "placa"),
    "RH": ("recursos humanos", "ferias", "admiss", "colaborador"),
    "Medição": ("medicao", "medir"),
    "Operações": ("operac", "obra", "projeto"),
    "Gerência": ("gerencia", "diretoria"),
    "TI": ("chamado", "tecnologia", "sistema", "suporte"),
    "Compliance": ("compliance", "auditoria", "conformidade"),
}


def _fold(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char)
    )


def source_field_kind(type_name: str | None) -> ZeevFieldKind:
    if type_name is None:
        return ZeevFieldKind.UNKNOWN
    name = _fold(type_name)
    if name in {
        "texto",
        "area de texto",
        "texto rico",
        "cpf",
        "cnpj",
        "placa",
        "email",
        "telefone",
        "telefone celular",
        "cep - seach and fill",
    }:
        return ZeevFieldKind.TEXT
    if name in {"numero", "moeda", "somente numeros"}:
        return ZeevFieldKind.NUMBER
    if name in {"data", "data e hora", "hora"}:
        return ZeevFieldKind.DATE
    if name in {"sim/nao", "booleano"}:
        return ZeevFieldKind.BOOLEAN
    if name in {"caixa de selecao", "lista de selecao", "lista de selecao unica"}:
        return ZeevFieldKind.CHOICE
    if name in {"pessoa", "usuario", "time"}:
        return ZeevFieldKind.USER
    if name in {"arquivo", "arquivo - visualizador", "anexo"}:
        return ZeevFieldKind.FILE
    if name in {"tabela", "grade"}:
        return ZeevFieldKind.TABLE
    return ZeevFieldKind.UNKNOWN


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _str_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _team_ids(value: Any) -> tuple[int, ...]:
    if not isinstance(value, list):
        return ()
    ids = {
        team_id
        for team in value
        if isinstance(team, dict)
        if (team_id := _int_or_none(team.get("id"))) is not None
    }
    return tuple(sorted(ids))


def catalog_field(field: ZeevFormField) -> ZeevFormFieldCatalogEntry:
    metadata = field.source_metadata
    kind = source_field_kind(field.type_name)
    return ZeevFormFieldCatalogEntry(
        external_id=field.external_id,
        name=field.name,
        label=field.label,
        zeev_type=field.type_name,
        kind=kind,
        required=field.required,
        options=field.options if kind is ZeevFieldKind.CHOICE else (),
        group_name=_str_or_none(metadata.get("groupName")),
        group_order=_int_or_none(metadata.get("groupOrder")),
        row_order=_int_or_none(metadata.get("rowOrder")),
        column_order=_int_or_none(metadata.get("columnOrder")),
        order=_int_or_none(metadata.get("order")),
        repeating=True if kind is ZeevFieldKind.TABLE else None,
    )


def candidate_areas(flow: ZeevFlowCatalogEntry) -> tuple[ZeevCandidateArea, ...]:
    sources = [("flow name", flow.name)]
    if flow.schema:
        sources.extend(
            ("section", field.group_name)
            for field in flow.schema.fields
            if field.group_name
        )
        sources.extend(
            ("field label", field.label) for field in flow.schema.fields if field.label
        )
    found: list[ZeevCandidateArea] = []
    for area, terms in _AREA_TERMS.items():
        evidence = tuple(
            dict.fromkeys(
                f'{source} contains "{term}"'
                for source, value in sources
                for term in terms
                if value and term in _fold(value)
            )
        )
        if evidence:
            found.append(ZeevCandidateArea(flow.external_id, area, evidence[:4]))
    return tuple(found)


@dataclass
class _ObservedField:
    types: set[str]
    occurrences: int = 0
    null_count: int = 0
    min_items: int | None = None
    max_items: int | None = None


@dataclass
class _RuntimeSample:
    instances: list[ZeevInstance]
    assignments: list[ZeevTask]
    report_checked: bool
    assignments_checked: bool
    rate_limited: bool


def profile_structure(records: list[dict[str, Any]]) -> tuple[ZeevStructureField, ...]:
    """Record shape, counts, and array lengths; discard every scalar value."""
    observed: dict[str, _ObservedField] = defaultdict(lambda: _ObservedField(set()))

    def visit(value: Any, path: str, depth: int) -> None:
        if depth > 12:
            return
        node = observed[path]
        node.occurrences += 1
        if value is None:
            node.types.add("null")
            node.null_count += 1
        elif isinstance(value, dict):
            node.types.add("object")
            for key, child in value.items():
                if isinstance(key, str):
                    visit(child, f"{path}.{key}" if path else key, depth + 1)
        elif isinstance(value, list):
            node.types.add("array")
            size = len(value)
            node.min_items = (
                size if node.min_items is None else min(node.min_items, size)
            )
            node.max_items = (
                size if node.max_items is None else max(node.max_items, size)
            )
            for child in value:
                visit(child, f"{path}[]", depth + 1)
        elif isinstance(value, bool):
            node.types.add("boolean")
        elif isinstance(value, (int, float)):
            node.types.add("number")
        else:
            node.types.add("string")

    for record in records:
        for key, value in record.items():
            visit(value, key, 0)
    return tuple(
        ZeevStructureField(
            path,
            tuple(sorted(node.types)),
            node.occurrences,
            node.null_count,
            node.min_items,
            node.max_items,
        )
        for path, node in sorted(observed.items())
    )


def _capabilities(
    report_checked: bool,
    assignments_checked: bool,
    schema_readable: bool,
    task_features: set[str],
    identity_states: dict[str, ZeevCapabilityState],
) -> tuple[ZeevCapability, ...]:
    validated = ZeevCapabilityState.LIVE_VALIDATED
    documented = ZeevCapabilityState.DOCUMENTED
    entries = (
        ("startable_flows", validated, "GET", "/api/2/requests/flows"),
        ("editable_flows", validated, "GET", "/api/2/flows/edit"),
        (
            "form_schema",
            validated if schema_readable else documented,
            "GET",
            "/api/2/flows/{flowid}/design/form",
        ),
        (
            "instance_report",
            validated if report_checked else documented,
            "GET",
            "/api/2/instances/report",
        ),
        (
            "pending_tasks",
            validated if assignments_checked else documented,
            "GET",
            "/api/2/assignments",
        ),
        (
            "finished_tasks",
            validated if "finished" in task_features else documented,
            "GET",
            "/api/2/instances/report",
        ),
        (
            "task_history",
            validated if "finished" in task_features else documented,
            "GET",
            "/api/2/instances/report",
        ),
        (
            "task_assignee",
            validated if "assignee" in task_features else documented,
            "GET",
            "/api/2/instances/report",
        ),
        (
            "task_team",
            validated if "team" in task_features else documented,
            "GET",
            "/api/2/instances/report",
        ),
        (
            "task_timestamps",
            validated if "timestamps" in task_features else documented,
            "GET",
            "/api/2/instances/report",
        ),
        (
            "users",
            identity_states.get("users", documented),
            "GET",
            "/api/2/users/{userid}",
        ),
        (
            "teams",
            identity_states.get("teams", documented),
            "GET",
            "/api/2/teams/{teamid}",
        ),
        (
            "roles",
            identity_states.get("roles", documented),
            "GET",
            "/api/2/positions/{positionid}",
        ),
        ("maintenance_groups", documented, "GET", "/api/2/groups/{groupid}"),
        ("attachment_download", ZeevCapabilityState.NOT_FOUND, None, None),
    )
    return tuple(ZeevCapability(*entry) for entry in entries)


class ZeevCatalogService:
    def __init__(self, client: ZeevClient, *, interval_seconds: float = 0.15) -> None:
        if interval_seconds < 0:
            raise ValueError("Zeev catalog interval cannot be negative")
        self._client = client
        self._interval_seconds = interval_seconds

    def _pace(self) -> None:
        if self._interval_seconds:
            time.sleep(self._interval_seconds)

    def _sample_attachment_form(
        self,
        instances: list[ZeevInstance],
        flows: list[ZeevFlowCatalogEntry],
        warnings: list[ZeevCatalogWarning],
    ) -> bool:
        by_id = {flow.external_id: flow for flow in flows}
        for index, instance in enumerate(instances):
            flow = by_id.get(instance.flow_id) if instance.flow_id else None
            if flow is None or flow.schema is None:
                continue
            file_names = tuple(
                field.name
                for field in flow.schema.fields
                if field.kind is ZeevFieldKind.FILE and field.name
            )[:3]
            if not file_names:
                continue
            self._pace()
            try:
                instances[index] = self._client.get_instance(
                    instance.external_id, form_field_names=file_names
                )
            except ZeevPermissionError:
                warnings.append(
                    ZeevCatalogWarning("instance_form", None, "PERMISSION_DENIED")
                )
            except ZeevRateLimitError:
                warnings.append(
                    ZeevCatalogWarning("instance_form", None, "RATE_LIMITED")
                )
                return True
            except (ZeevProtocolError, ZeevUnavailableError):
                warnings.append(
                    ZeevCatalogWarning("instance_form", None, "PROBE_UNAVAILABLE")
                )
            break
        return False

    def _probe_identities(
        self,
        instance: ZeevInstance,
        warnings: list[ZeevCatalogWarning],
    ) -> dict[str, ZeevCapabilityState]:
        requester = instance.source_metadata.get("requester")
        if not isinstance(requester, dict):
            return {}
        team = requester.get("team")
        position = requester.get("position")
        probes = (
            ("users", _int_or_none(requester.get("id")), self._client.probe_user),
            (
                "teams",
                _int_or_none(team.get("id")) if isinstance(team, dict) else None,
                self._client.probe_team,
            ),
            (
                "roles",
                _int_or_none(position.get("id"))
                if isinstance(position, dict)
                else None,
                self._client.probe_position,
            ),
        )
        states: dict[str, ZeevCapabilityState] = {}
        for name, resource_id, probe in probes:
            if resource_id is None or resource_id <= 0:
                continue
            self._pace()
            try:
                probe(resource_id)
                states[name] = ZeevCapabilityState.LIVE_VALIDATED
            except ZeevPermissionError:
                states[name] = ZeevCapabilityState.PERMISSION_DENIED
                warnings.append(ZeevCatalogWarning(name, None, "PERMISSION_DENIED"))
            except ZeevRateLimitError:
                warnings.append(ZeevCatalogWarning(name, None, "RATE_LIMITED"))
                break
            except (ZeevProtocolError, ZeevUnavailableError):
                warnings.append(ZeevCatalogWarning(name, None, "PROBE_UNAVAILABLE"))
        return states

    def _sample_runtime(
        self,
        flows: list[ZeevFlowCatalogEntry],
        warnings: list[ZeevCatalogWarning],
    ) -> _RuntimeSample:
        now = datetime.now(timezone.utc)
        self._pace()
        try:
            instances = self._client.query_instances(
                ZeevInstanceQuery(
                    start=now - timedelta(days=1),
                    end=now,
                    page_size=5,
                    max_pages=1,
                    max_records=5,
                )
            )
        except ZeevRateLimitError:
            warnings.append(ZeevCatalogWarning("instance_report", None, "RATE_LIMITED"))
            return _RuntimeSample([], [], False, False, True)
        except (ZeevPermissionError, ZeevProtocolError, ZeevUnavailableError):
            warnings.append(
                ZeevCatalogWarning("instance_report", None, "PROBE_UNAVAILABLE")
            )
            return _RuntimeSample([], [], False, False, False)
        self._pace()
        try:
            assignments = self._client.list_my_assignments(page_size=5)
        except ZeevRateLimitError:
            warnings.append(ZeevCatalogWarning("assignments", None, "RATE_LIMITED"))
            return _RuntimeSample(instances, [], True, False, True)
        except (ZeevPermissionError, ZeevProtocolError, ZeevUnavailableError):
            warnings.append(
                ZeevCatalogWarning("assignments", None, "PROBE_UNAVAILABLE")
            )
            assignments = []
            assignments_checked = False
        else:
            assignments_checked = True
        rate_limited = self._sample_attachment_form(instances, flows, warnings)
        return _RuntimeSample(
            instances, assignments, True, assignments_checked, rate_limited
        )

    def discover(self, *, sample_instances: bool = True) -> ZeevSourceCatalog:
        warnings: list[ZeevCatalogWarning] = []
        startable = self._client.list_flows()
        self._pace()
        editable = self._client.list_editable_flows()
        self._pace()
        services = self._client.list_services()
        start_by_id = {flow.external_id: flow for flow in startable}
        edit_by_id = {flow.external_id: flow for flow in editable}
        flows: list[ZeevFlowCatalogEntry] = []
        rate_limited = False
        for flow_id in sorted(start_by_id.keys() | edit_by_id.keys()):
            start = start_by_id.get(flow_id)
            edit = edit_by_id.get(flow_id)
            source = edit or start
            if source is None:
                continue
            metadata = edit.source_metadata if edit else {}
            schema: ZeevFormSchemaCatalog | None = None
            state = ZeevSchemaState.SCHEMA_UNAVAILABLE
            design_elements: tuple[ZeevDesignElement, ...] = ()
            design_state = ZeevSchemaState.SCHEMA_UNAVAILABLE
            if not rate_limited:
                self._pace()
                try:
                    fields = self._client.get_flow_form_fields(flow_id)
                    ordered = sorted(
                        (catalog_field(field) for field in fields),
                        key=lambda field: (
                            field.group_order
                            if field.group_order is not None
                            else 2**31,
                            field.row_order if field.row_order is not None else 2**31,
                            field.column_order
                            if field.column_order is not None
                            else 2**31,
                            field.order if field.order is not None else 2**31,
                            field.external_id,
                        ),
                    )
                    schema = ZeevFormSchemaCatalog(flow_id, tuple(ordered))
                    state = ZeevSchemaState.AVAILABLE
                except ZeevPermissionError:
                    state = ZeevSchemaState.PERMISSION_DENIED
                except ZeevRateLimitError:
                    rate_limited = True
                    warnings.append(ZeevCatalogWarning("catalog", None, "RATE_LIMITED"))
                except (ZeevProtocolError, ZeevUnavailableError):
                    state = ZeevSchemaState.PROTOCOL_ERROR
            if not rate_limited:
                self._pace()
                try:
                    design_elements = tuple(
                        self._client.get_flow_design_elements(flow_id)
                    )
                    design_state = ZeevSchemaState.AVAILABLE
                except ZeevPermissionError:
                    design_state = ZeevSchemaState.PERMISSION_DENIED
                except ZeevRateLimitError:
                    rate_limited = True
                    warnings.append(ZeevCatalogWarning("catalog", None, "RATE_LIMITED"))
                except (ZeevProtocolError, ZeevUnavailableError):
                    design_state = ZeevSchemaState.PROTOCOL_ERROR
            if state is not ZeevSchemaState.AVAILABLE:
                warnings.append(ZeevCatalogWarning("flow_schema", flow_id, state.value))
            if design_state is not ZeevSchemaState.AVAILABLE:
                warnings.append(
                    ZeevCatalogWarning("flow_design", flow_id, design_state.value)
                )
            flows.append(
                ZeevFlowCatalogEntry(
                    external_id=flow_id,
                    uid=source.uid or (start.uid if start else None),
                    version=source.version
                    if source.version is not None
                    else (start.version if start else None),
                    name=source.name or (start.name if start else ""),
                    description=_str_or_none(metadata.get("flowDescription"))
                    or _str_or_none(
                        start.source_metadata.get("description") if start else None
                    ),
                    active=metadata.get("active")
                    if isinstance(metadata.get("active"), bool)
                    else None,
                    deployed=source.deployed
                    if source.deployed is not None
                    else (start.deployed if start else None),
                    startable=start is not None,
                    editable=edit is not None,
                    startable_team_ids=_team_ids(
                        start.source_metadata.get("teams") if start else None
                    ),
                    category_id=_int_or_none(metadata.get("categoryId")),
                    category_name=_str_or_none(metadata.get("categoryName")),
                    team_name=_str_or_none(metadata.get("teamName")),
                    parent_id=_int_or_none(metadata.get("parentId")),
                    execution_mode=_str_or_none(metadata.get("executionMode")),
                    last_deploy=_str_or_none(metadata.get("lastDeploy"))
                    or _str_or_none(
                        start.source_metadata.get("lastDeploy") if start else None
                    ),
                    schema_state=state,
                    schema=schema,
                    design_state=design_state,
                    design_elements=design_elements,
                )
            )
        flows.sort(key=lambda flow: (_fold(flow.name), flow.external_id))
        runtime = _RuntimeSample([], [], False, False, rate_limited)
        if sample_instances and not rate_limited:
            runtime = self._sample_runtime(flows, warnings)
        instances = runtime.instances
        assignments = runtime.assignments
        rate_limited = runtime.rate_limited
        tasks = [task for instance in instances for task in instance.tasks]
        task_records = [task.source_metadata for task in tasks + assignments]
        task_features: set[str] = set()
        if any(task.active is False for task in tasks):
            task_features.add("finished")
        if any(task.started_at or task.ended_at for task in tasks):
            task_features.add("timestamps")
        for task in tasks:
            assignees = task.source_metadata.get("assignees")
            if isinstance(assignees, list) and assignees:
                task_features.add("assignee")
                if any(
                    isinstance(assignee, dict)
                    and isinstance(assignee.get("team"), dict)
                    for assignee in assignees
                ):
                    task_features.add("team")
        identity_states = (
            self._probe_identities(instances[0], warnings)
            if instances and not rate_limited
            else {}
        )
        instance_structure = profile_structure(
            [instance.source_metadata for instance in instances]
        )
        task_structure = profile_structure(task_records)
        attachment_state = (
            ZeevAttachmentReadState.REFERENCE_ONLY
            if any(
                field.kind is ZeevFieldKind.FILE
                for flow in flows
                if flow.schema
                for field in flow.schema.fields
            )
            else ZeevAttachmentReadState.NOT_FOUND_IN_PUBLIC_API
        )
        return ZeevSourceCatalog(
            flows=tuple(flows),
            services=tuple(
                sorted(
                    (
                        ZeevServiceCatalogEntry(
                            service.external_id,
                            service.uid,
                            service.name,
                            service.flow_id,
                            _str_or_none(service.source_metadata.get("description")),
                            service.source_metadata.get("deploy")
                            if isinstance(service.source_metadata.get("deploy"), bool)
                            else None,
                            _str_or_none(service.source_metadata.get("lastDeploy")),
                        )
                        for service in services
                    ),
                    key=lambda service: (_fold(service.name), service.external_id),
                )
            ),
            capabilities=_capabilities(
                runtime.report_checked,
                runtime.assignments_checked,
                any(flow.schema_state is ZeevSchemaState.AVAILABLE for flow in flows),
                task_features,
                identity_states,
            ),
            warnings=tuple(warnings),
            candidates=tuple(
                candidate for flow in flows for candidate in candidate_areas(flow)
            ),
            instance_structure=instance_structure,
            task_structure=task_structure,
            instance_sample_count=len(instances),
            task_sample_count=len(task_records),
            attachment_read=attachment_state,
        )
