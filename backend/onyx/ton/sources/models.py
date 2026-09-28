from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AcquisitionType(StrEnum):
    FILE_UPLOAD = "FILE_UPLOAD"
    API = "API"
    DATABASE = "DATABASE"
    MANUAL = "MANUAL"
    CONNECTED_SERVICE = "CONNECTED_SERVICE"


class SourceStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    CONFIGURING = "CONFIGURING"
    ERROR = "ERROR"


class Sensitivity(StrEnum):
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class ImportStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ImportTrigger(StrEnum):
    MANUAL_UPLOAD = "MANUAL_UPLOAD"
    SCHEDULED = "SCHEDULED"
    API_SYNC = "API_SYNC"
    SYSTEM = "SYSTEM"
    RETRY = "RETRY"


class SourceFormat(StrEnum):
    JSON = "JSON"
    XLS = "XLS"
    XLSX = "XLSX"
    XLSM = "XLSM"
    CSV = "CSV"
    PDF = "PDF"


class SourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    display_name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    acquisition_type: AcquisitionType
    status: SourceStatus = SourceStatus.CONFIGURING
    sensitivity: Sensitivity = Sensitivity.RESTRICTED
    group_ids: list[int] = Field(default_factory=list, max_length=100)


class SourceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    acquisition_type: AcquisitionType
    status: SourceStatus
    sensitivity: Sensitivity


class SourceView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    key: str
    display_name: str
    description: str | None
    acquisition_type: AcquisitionType
    status: SourceStatus
    sensitivity: Sensitivity
    created_at: datetime
    updated_at: datetime


class ImportRunView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_id: UUID
    status: ImportStatus
    trigger: ImportTrigger
    acquisition_type: AcquisitionType
    initiated_by: UUID | None
    started_at: datetime
    finished_at: datetime | None
    snapshot_count: int
    error_code: str | None
    cleanup_required: bool


class SnapshotView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_id: UUID
    import_run_id: UUID
    original_filename: str
    media_type: str
    format: SourceFormat
    size_bytes: int
    checksum: str
    extracted_at: datetime
    duplicate_of_id: UUID | None


class SourceLocator(BaseModel):
    """Reference to evidence; never a copy of business values."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    snapshot_id: UUID
    sheet_name: str | None = Field(default=None, max_length=255)
    row_number: int | None = Field(default=None, ge=1)
    page_number: int | None = Field(default=None, ge=1)
    source_record_key: str | None = Field(default=None, max_length=500)
    json_pointer: str | None = Field(
        default=None, max_length=1000, pattern=r"^(?:/.*)?$"
    )
