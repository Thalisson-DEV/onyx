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
