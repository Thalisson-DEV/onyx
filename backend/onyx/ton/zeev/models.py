from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


@dataclass(frozen=True)
class ZeevFlow:
    external_id: int
    name: str
    uid: str | None
    version: int | None
    deployed: bool | None
    source_metadata: dict[str, Any]


@dataclass(frozen=True)
class ZeevService:
    external_id: int
    name: str
    uid: str | None
    flow_id: int | None
    source_metadata: dict[str, Any]


@dataclass(frozen=True)
class ZeevFormField:
    external_id: int
    name: str
    label: str | None
    type_name: str | None
    required: bool | None
    options: tuple[str, ...]
    source_metadata: dict[str, Any]


@dataclass(frozen=True)
class ZeevDesignElement:
    external_id: int
    title: str | None
    type_name: str | None
    order: int
    page: int | None
    business_hours: bool | None
    timeout: float | None
    editable_field_count: int | None
    required_file_count: int | None
    user_representation: str
    user_count: int | None


@dataclass(frozen=True)
class ZeevTask:
    external_id: int
    name: str | None
    active: bool | None
    started_at: str | None
    ended_at: str | None
    source_metadata: dict[str, Any]


@dataclass(frozen=True)
class ZeevInstance:
    external_id: int
    active: bool | None
    started_at: str | None
    ended_at: str | None
    flow_id: int | None
    tasks: tuple[ZeevTask, ...]
    source_metadata: dict[str, Any]


@dataclass(frozen=True)
class ZeevInstanceQuery:
    start: datetime
    end: datetime
    flow_id: int | None = None
    page_size: int = 10
    max_pages: int = 2
    max_records: int = 20

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("Zeev query dates must include a timezone")
        seconds = (self.end - self.start).total_seconds()
        if not 0 < seconds <= 7 * 86400:
            raise ValueError("Zeev query range must be at most seven days")
        if not 1 <= self.page_size <= 20:
            raise ValueError("Zeev page size must be between 1 and 20")
        if not 1 <= self.max_pages <= 5:
            raise ValueError("Zeev max pages must be between 1 and 5")
        if not 1 <= self.max_records <= 100:
            raise ValueError("Zeev max records must be between 1 and 100")
        if self.flow_id is not None and self.flow_id <= 0:
            raise ValueError("Zeev flow ID must be positive")


class ZeevHealthState(str, Enum):
    DISABLED = "DISABLED"
    UNCONFIGURED = "UNCONFIGURED"
    AUTHENTICATING = "AUTHENTICATING"
    AVAILABLE = "AVAILABLE"
    AUTH_ERROR = "AUTH_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class ZeevHealth:
    state: ZeevHealthState


class ZeevSchemaState(str, Enum):
    AVAILABLE = "AVAILABLE"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    SCHEMA_UNAVAILABLE = "SCHEMA_UNAVAILABLE"
    PROTOCOL_ERROR = "PROTOCOL_ERROR"


class ZeevFieldKind(str, Enum):
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    DATE = "DATE"
    BOOLEAN = "BOOLEAN"
    CHOICE = "CHOICE"
    USER = "USER"
    FILE = "FILE"
    TABLE = "TABLE"
    UNKNOWN = "UNKNOWN"


class ZeevCapabilityState(str, Enum):
    LIVE_VALIDATED = "LIVE_VALIDATED"
    DOCUMENTED = "DOCUMENTED"
    NOT_FOUND = "NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"


class ZeevAttachmentReadState(str, Enum):
    SUPPORTED_AND_VALIDATED = "SUPPORTED_AND_VALIDATED"
    SUPPORTED_NOT_VALIDATED = "SUPPORTED_NOT_VALIDATED"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    NOT_FOUND_IN_PUBLIC_API = "NOT_FOUND_IN_PUBLIC_API"
    PERMISSION_BLOCKED = "PERMISSION_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ZeevFormFieldCatalogEntry:
    external_id: int
    name: str
    label: str | None
    zeev_type: str | None
    kind: ZeevFieldKind
    required: bool | None
    options: tuple[str, ...]
    group_name: str | None
    group_order: int | None
    row_order: int | None
    column_order: int | None
    order: int | None
    repeating: bool | None


@dataclass(frozen=True)
class ZeevFormSchemaCatalog:
    flow_id: int
    fields: tuple[ZeevFormFieldCatalogEntry, ...]


@dataclass(frozen=True)
class ZeevFlowCatalogEntry:
    external_id: int
    uid: str | None
    version: int | None
    name: str
    description: str | None
    active: bool | None
    deployed: bool | None
    startable: bool
    editable: bool
    startable_team_ids: tuple[int, ...]
    category_id: int | None
    category_name: str | None
    team_name: str | None
    parent_id: int | None
    execution_mode: str | None
    last_deploy: str | None
    schema_state: ZeevSchemaState
    schema: ZeevFormSchemaCatalog | None
    design_state: ZeevSchemaState
    design_elements: tuple[ZeevDesignElement, ...]


@dataclass(frozen=True)
class ZeevServiceCatalogEntry:
    external_id: int
    uid: str | None
    name: str
    flow_id: int | None
    description: str | None
    deployed: bool | None
    last_deploy: str | None


@dataclass(frozen=True)
class ZeevCatalogWarning:
    resource: str
    external_id: int | None
    state: str


@dataclass(frozen=True)
class ZeevCapability:
    name: str
    state: ZeevCapabilityState
    method: str | None
    path: str | None


@dataclass(frozen=True)
class ZeevCandidateArea:
    flow_id: int
    area: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ZeevStructureField:
    path: str
    observed_types: tuple[str, ...]
    occurrences: int
    null_count: int
    min_items: int | None
    max_items: int | None


@dataclass(frozen=True)
class ZeevSourceCatalog:
    flows: tuple[ZeevFlowCatalogEntry, ...]
    services: tuple[ZeevServiceCatalogEntry, ...]
    capabilities: tuple[ZeevCapability, ...]
    warnings: tuple[ZeevCatalogWarning, ...]
    candidates: tuple[ZeevCandidateArea, ...]
    instance_structure: tuple[ZeevStructureField, ...]
    task_structure: tuple[ZeevStructureField, ...]
    instance_sample_count: int
    task_sample_count: int
    attachment_read: ZeevAttachmentReadState

    @property
    def field_count(self) -> int:
        return sum(len(flow.schema.fields) for flow in self.flows if flow.schema)

    @property
    def design_element_count(self) -> int:
        return sum(len(flow.design_elements) for flow in self.flows)
