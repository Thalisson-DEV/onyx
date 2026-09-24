import logging
import os
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
from urllib.parse import urlsplit

import httpx

from onyx.ton.zeev.models import (
    ZeevFlow,
    ZeevFormField,
    ZeevHealth,
    ZeevHealthState,
    ZeevInstance,
    ZeevInstanceQuery,
    ZeevService,
    ZeevTask,
)
from onyx.utils.retry_after import parse_retry_after_seconds

logger = logging.getLogger(__name__)


class ZeevError(Exception):
    pass


class ZeevConfigurationError(ZeevError):
    pass


class ZeevAuthenticationError(ZeevError):
    pass


class ZeevPermissionError(ZeevError):
    pass


class ZeevRateLimitError(ZeevError):
    pass


class ZeevUnavailableError(ZeevError):
    pass


class ZeevProtocolError(ZeevError):
    pass


class ZeevReadOnlyViolation(ZeevError):
    pass


@dataclass(frozen=True)
class ZeevConfig:
    enabled: bool
    base_url: str
    username: str | None = field(default=None, repr=False)
    password: str | None = field(default=None, repr=False)
    token: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        parsed = urlsplit(self.base_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.path not in ("", "/")
        ):
            raise ZeevConfigurationError("Zeev base URL must be an HTTPS origin")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ZeevConfigurationError(
                "Zeev base URL must not contain credentials or query"
            )

    @classmethod
    def from_env(cls) -> "ZeevConfig":
        enabled = os.getenv("ZEEV_ENABLED", "false").lower() == "true"
        return cls(
            enabled=enabled,
            base_url=os.getenv("ZEEV_BASE_URL", "https://nucleo.zeev.it"),
            username=os.getenv("ZEEV_USERNAME"),
            password=os.getenv("ZEEV_PASSWORD"),
            token=os.getenv("ZEEV_TOKEN"),
        )


class _Operation(Enum):
    LOGIN = ("POST", "/api/2/tokens")
    IDENTITY = ("GET", "/api/2/tokens")
    FLOWS = ("GET", "/api/2/requests/flows")
    EDITABLE_FLOWS = ("GET", "/api/2/flows/edit")
    SERVICES = ("GET", "/api/2/requests/services")
    FORM = ("GET", "/api/2/flows/{flowid}/design/form")
    INSTANCES = ("GET", "/api/2/instances/report")
    INSTANCES_POST = ("POST", "/api/2/instances/report")
    INSTANCE = ("GET", "/api/2/instances/{instanceid}")
    ASSIGNMENTS = ("GET", "/api/2/assignments")

    @property
    def method(self) -> str:
        return self.value[0]

    @property
    def path(self) -> str:
        return self.value[1]


def _assert_read_only(method: str, path: str, operation: _Operation) -> None:
    if method in {"PUT", "PATCH", "DELETE"}:
        raise ZeevReadOnlyViolation("Zeev mutation method is blocked")
    if method == "POST" and operation not in {
        _Operation.LOGIN,
        _Operation.INSTANCES_POST,
    }:
        raise ZeevReadOnlyViolation("Zeev POST operation is not allowed")
    if method not in {"GET", "POST"}:
        raise ZeevReadOnlyViolation("Zeev method is not allowed")
    if method != operation.method or path != operation.path:
        raise ZeevReadOnlyViolation("Zeev operation is outside the read-only allowlist")


def _object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ZeevProtocolError("Zeev returned an unexpected object")
    return value


def _array(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ZeevProtocolError("Zeev returned an unexpected list")
    return [_object(item) for item in value]


def _int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ZeevProtocolError("Zeev record is missing an integer ID")
    return value


def _optional_int(value: Any) -> int | None:
    return None if value is None else _int(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ZeevProtocolError("Zeev returned an unexpected string field")
    return value


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ZeevProtocolError("Zeev returned an unexpected boolean field")
    return value


class ZeevClient:
    """Only audited Zeev operations are exposed to higher-level code."""

    def __init__(
        self,
        config: ZeevConfig,
        http_client: httpx.Client | None = None,
        audit_call: Callable[[str, str], None] | None = None,
        audit_rate_headers: Callable[[tuple[str, ...]], None] | None = None,
    ) -> None:
        self._config = config
        self._http = http_client or httpx.Client(
            base_url=config.base_url,
            timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0),
            verify=True,
            follow_redirects=False,
        )
        self._owns_http = http_client is None
        self._audit_call = audit_call
        self._audit_rate_headers = audit_rate_headers
        self._token_lock = threading.Lock()
        self._temporary_token: str | None = None
        self._token_expires_at = 0.0

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> "ZeevClient":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _login(self) -> str:
        if not self._config.username or not self._config.password:
            raise ZeevConfigurationError("Zeev login credentials are not configured")
        response = self._send(
            _Operation.LOGIN,
            json_body={
                "login": self._config.username,
                "password": self._config.password,
            },
            authenticated=False,
        )
        token = _object(response).get("temporaryToken")
        if not isinstance(token, str) or not token:
            raise ZeevProtocolError("Zeev login did not return a temporary token")
        return token

    def _token(self, stale_token: str | None = None) -> str:
        if self._config.token:
            return self._config.token
        with self._token_lock:
            if stale_token is not None and self._temporary_token == stale_token:
                self._temporary_token = None
            if self._temporary_token and time.monotonic() < self._token_expires_at:
                return self._temporary_token
            token = self._login()
            self._temporary_token = token
            self._token_expires_at = time.monotonic() + 8 * 60
            return token

    @staticmethod
    def _validate_path(operation: _Operation, path: str) -> None:
        template = operation.path
        _assert_read_only(operation.method, template, operation)
        if "{" in path or "}" in path or not path.startswith("/api/2/"):
            raise ZeevReadOnlyViolation("Invalid Zeev path")
        if "{" in template:
            prefix, suffix = template.split("{", 1)
            suffix = suffix.split("}", 1)[1]
            identifier = path.removeprefix(prefix).removesuffix(suffix)
            if (
                not path.startswith(prefix)
                or not path.endswith(suffix)
                or not identifier.isdecimal()
                or int(identifier) <= 0
            ):
                raise ZeevReadOnlyViolation("Invalid Zeev resource ID")
        elif path != template:
            raise ZeevReadOnlyViolation("Zeev path is outside the allowlist")

    @staticmethod
    def _validate_report_filter(filters: dict[str, Any] | None) -> None:
        if filters is None:
            raise ZeevReadOnlyViolation("Zeev report needs bounded filters")
        try:
            start = datetime.fromisoformat(filters["startDateIntervalBegin"])
            end = datetime.fromisoformat(filters["startDateIntervalEnd"])
            page = filters["pageNumber"]
            size = filters["recordsPerPage"]
            ZeevInstanceQuery(start=start, end=end, page_size=size, max_pages=page)
        except (KeyError, TypeError, ValueError) as exc:
            raise ZeevReadOnlyViolation("Zeev report filters are unbounded") from exc

    @classmethod
    def _validate_request(
        cls,
        operation: _Operation,
        path: str,
        params: dict[str, Any] | None,
        json_body: dict[str, Any] | None,
    ) -> None:
        cls._validate_path(operation, path)
        if json_body is not None and operation not in {
            _Operation.LOGIN,
            _Operation.INSTANCES_POST,
        }:
            raise ZeevReadOnlyViolation("Zeev JSON body is outside the allowlist")
        if operation is _Operation.INSTANCES:
            cls._validate_report_filter(params)
        if operation is _Operation.INSTANCES_POST:
            cls._validate_report_filter(json_body)

    def _send(
        self,
        operation: _Operation,
        *,
        path: str | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        authenticated: bool = True,
    ) -> Any:
        if not self._config.enabled:
            raise ZeevConfigurationError("Zeev is disabled")
        if path is None:
            path = operation.path
        self._validate_request(operation, path, params, json_body)

        refreshed = False
        for attempt in range(3):
            headers = {"Accept": "application/json"}
            used_token: str | None = None
            if authenticated:
                used_token = self._token()
                headers["Authorization"] = f"Bearer {used_token}"
            started = time.monotonic()
            try:
                if self._audit_call is not None:
                    self._audit_call(operation.method, operation.path)
                response = self._http.request(
                    operation.method,
                    path,
                    params=params,
                    json=json_body,
                    headers=headers,
                )
            except httpx.RequestError as exc:
                if attempt == 2:
                    raise ZeevUnavailableError("Zeev request failed") from exc
                time.sleep(self._backoff(attempt, None))
                continue
            logger.info(
                "zeev operation=%s status=%d duration_ms=%d attempt=%d",
                operation.name,
                response.status_code,
                int((time.monotonic() - started) * 1000),
                attempt + 1,
            )
            if self._audit_rate_headers is not None:
                self._audit_rate_headers(
                    tuple(
                        sorted(
                            name
                            for name in response.headers
                            if name.lower().startswith("x-ratelimit")
                            or name.lower() == "retry-after"
                        )
                    )
                )
            if response.status_code == 401:
                if authenticated and not self._config.token and not refreshed:
                    refreshed = True
                    self._token(stale_token=used_token)
                    continue
                raise ZeevAuthenticationError("Zeev authentication failed")
            if response.status_code == 403:
                raise ZeevPermissionError("Zeev access denied")
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == 2:
                    if response.status_code == 429:
                        raise ZeevRateLimitError("Zeev rate limit reached")
                    raise ZeevUnavailableError("Zeev service unavailable")
                time.sleep(self._backoff(attempt, response.headers.get("Retry-After")))
                continue
            if response.status_code == 404:
                raise ZeevProtocolError("Zeev resource was not found")
            if response.status_code >= 400:
                raise ZeevProtocolError(f"Zeev returned HTTP {response.status_code}")
            try:
                return response.json()
            except ValueError as exc:
                raise ZeevProtocolError("Zeev returned invalid JSON") from exc
        raise ZeevUnavailableError("Zeev retry limit reached")

    @staticmethod
    def _backoff(attempt: int, retry_after: str | None) -> float:
        requested = parse_retry_after_seconds(retry_after)
        if requested is not None:
            return min(requested, 30.0)
        return min(0.5 * 2**attempt + random.uniform(0, 0.25), 3.0)

    def authenticate(self) -> None:
        self._token()

    def health_check(self) -> ZeevHealth:
        if not self._config.enabled:
            return ZeevHealth(ZeevHealthState.DISABLED)
        try:
            self._send(_Operation.IDENTITY)
        except ZeevConfigurationError:
            return ZeevHealth(ZeevHealthState.UNCONFIGURED)
        except ZeevAuthenticationError:
            return ZeevHealth(ZeevHealthState.AUTH_ERROR)
        except ZeevPermissionError:
            return ZeevHealth(ZeevHealthState.PERMISSION_ERROR)
        except ZeevRateLimitError:
            return ZeevHealth(ZeevHealthState.RATE_LIMITED)
        except (ZeevUnavailableError, ZeevProtocolError):
            return ZeevHealth(ZeevHealthState.UNAVAILABLE)
        return ZeevHealth(ZeevHealthState.AVAILABLE)

    def list_flows(self) -> list[ZeevFlow]:
        records = _array(self._send(_Operation.FLOWS))
        return [
            ZeevFlow(
                external_id=_int(row.get("id")),
                name=_optional_str(row.get("name")) or "",
                uid=_optional_str(row.get("uid")),
                version=_optional_int(row.get("version")),
                deployed=_optional_bool(row.get("deploy")),
                source_metadata=row,
            )
            for row in records
        ]

    def list_editable_flows(self) -> list[ZeevFlow]:
        payload = self._send(_Operation.EDITABLE_FLOWS)
        records = _array(payload) if isinstance(payload, list) else [_object(payload)]
        return [
            ZeevFlow(
                external_id=_int(row.get("flowId")),
                name=_optional_str(row.get("flowName")) or "",
                uid=_optional_str(row.get("flowUid")),
                version=_optional_int(row.get("flowVersion")),
                deployed=_optional_bool(row.get("deploy")),
                source_metadata=row,
            )
            for row in records
        ]

    def list_services(self) -> list[ZeevService]:
        return [
            ZeevService(
                external_id=_int(row.get("id")),
                name=_optional_str(row.get("name")) or "",
                uid=_optional_str(row.get("uid")),
                flow_id=_optional_int(_object(row["flow"]).get("id"))
                if row.get("flow") is not None
                else None,
                source_metadata=row,
            )
            for row in _array(self._send(_Operation.SERVICES))
        ]

    def get_flow_form_fields(self, flow_id: int) -> list[ZeevFormField]:
        if flow_id <= 0:
            raise ValueError("Zeev flow ID must be positive")
        payload = self._send(
            _Operation.FORM, path=f"/api/2/flows/{flow_id}/design/form"
        )
        records = _array(payload) if isinstance(payload, list) else [_object(payload)]
        return [
            ZeevFormField(
                external_id=_int(row.get("fieldId")),
                name=_optional_str(row.get("name")) or "",
                label=_optional_str(row.get("label")),
                type_name=_optional_str(row.get("typeName")),
                required=_optional_bool(row.get("required")),
                options=tuple(str(option) for option in row.get("attributes") or []),
                source_metadata=row,
            )
            for row in records
        ]

    @staticmethod
    def _parse_instance(row: dict[str, Any]) -> ZeevInstance:
        flow = row.get("flow")
        flow_id = _optional_int(_object(flow).get("id")) if flow is not None else None
        tasks = tuple(
            ZeevTask(
                external_id=_int(task.get("id")),
                name=_optional_str(_object(task.get("task")).get("name"))
                if task.get("task") is not None
                else None,
                active=_optional_bool(task.get("active")),
                started_at=_optional_str(task.get("startDateTime")),
                ended_at=_optional_str(task.get("endDateTime")),
                source_metadata=task,
            )
            for task in _array(row.get("instanceTasks") or [])
        )
        return ZeevInstance(
            external_id=_int(row.get("id")),
            active=_optional_bool(row.get("active")),
            started_at=_optional_str(row.get("startDateTime")),
            ended_at=_optional_str(row.get("endDateTime")),
            flow_id=flow_id,
            tasks=tasks,
            source_metadata=row,
        )

    def get_instance(self, instance_id: int) -> ZeevInstance:
        if instance_id <= 0:
            raise ValueError("Zeev instance ID must be positive")
        return self._parse_instance(
            _object(
                self._send(
                    _Operation.INSTANCE,
                    path=f"/api/2/instances/{instance_id}",
                    params={
                        "showPendingInstanceTasks": "true",
                        "showFinishedInstanceTasks": "true",
                    },
                )
            )
        )

    def query_instances(
        self, query: ZeevInstanceQuery, *, use_post: bool = False
    ) -> list[ZeevInstance]:
        found: list[ZeevInstance] = []
        previous_ids: set[int] | None = None
        seen_ids: set[int] = set()
        for page in range(1, query.max_pages + 1):
            params: dict[str, Any] = {
                "startDateIntervalBegin": query.start.isoformat(),
                "startDateIntervalEnd": query.end.isoformat(),
                "recordsPerPage": query.page_size,
                "pageNumber": page,
                "showPendingInstanceTasks": "true",
                "showFinishedInstanceTasks": "true",
            }
            if query.flow_id is not None:
                params["flowId"] = query.flow_id
            payload = (
                self._send(_Operation.INSTANCES_POST, json_body=params)
                if use_post
                else self._send(_Operation.INSTANCES, params=params)
            )
            records = [self._parse_instance(row) for row in _array(payload)]
            page_ids = {record.external_id for record in records}
            if not records or page_ids == previous_ids or page_ids & seen_ids:
                break
            found.extend(records[: query.max_records - len(found)])
            seen_ids.update(page_ids)
            previous_ids = page_ids
            if len(records) < query.page_size or len(found) >= query.max_records:
                break
        return found

    def list_my_assignments(self, page_size: int = 10) -> list[ZeevTask]:
        if not 1 <= page_size <= 20:
            raise ValueError("Zeev page size must be between 1 and 20")
        records = _array(
            self._send(
                _Operation.ASSIGNMENTS,
                params={"pageNumber": 1, "recordsPerPage": page_size},
            )
        )
        return [
            ZeevTask(
                external_id=_int(row.get("id")),
                name=_optional_str(row.get("taskName")),
                active=_optional_bool(row.get("active")),
                started_at=_optional_str(row.get("startDateTime")),
                ended_at=None,
                source_metadata=row,
            )
            for row in records
        ]
