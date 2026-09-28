"""Bounded container checks. Uploaded code and macros are never executed."""

import hashlib
from io import BytesIO
from pathlib import PurePath
from typing import BinaryIO
from zipfile import BadZipFile, ZipFile

import olefile
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from pydantic import BaseModel, ConfigDict

from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.sources.models import SourceFormat
from onyx.utils.zip_safety import validate_zip_archive

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_CONTENT_TYPES_BYTES = 256 * 1024
MEDIA_TYPES: dict[SourceFormat, str] = {
    SourceFormat.JSON: "application/json",
    SourceFormat.XLS: "application/vnd.ms-excel",
    SourceFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    SourceFormat.XLSM: "application/vnd.ms-excel.sheet.macroenabled.12",
    SourceFormat.CSV: "text/csv",
    SourceFormat.PDF: "application/pdf",
}


class ValidatedUpload(BaseModel):
    model_config = ConfigDict(frozen=True)
    content: bytes
    filename: str
    media_type: str
    format: SourceFormat
    checksum: str


def validate_upload(
    stream: BinaryIO, filename: str, media_type: str
) -> ValidatedUpload:
    if not filename or len(filename) > 255 or any(c in filename for c in "\\/\x00\r\n"):
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Invalid source filename")
    try:
        format = SourceFormat(PurePath(filename).suffix.lstrip(".").upper())
    except ValueError:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "Unsupported source format"
        ) from None
    if format == SourceFormat.JSON:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "JSON requires connected capture")
    if media_type.split(";", 1)[0].strip().lower() != MEDIA_TYPES[format]:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "Source extension and media type differ"
        )
    content = stream.read(MAX_UPLOAD_BYTES + 1)
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Source upload size is invalid")
    try:
        if format in (SourceFormat.XLSX, SourceFormat.XLSM):
            _check_workbook_container(content, format)
        elif format == SourceFormat.XLS:
            with olefile.OleFileIO(BytesIO(content)) as compound:
                if not (compound.exists("Workbook") or compound.exists("Book")):
                    raise ValueError("Not a workbook")
        elif format == SourceFormat.PDF:
            if not content.startswith(b"%PDF-") or b"%%EOF" not in content[-1024:]:
                raise ValueError("Not a PDF")
        else:
            # CSV has no magic signature. Accept UTF-8 text, without binary controls.
            decoded = content.decode("utf-8-sig")
            if any(ord(c) < 32 and c not in "\t\r\n" for c in decoded):
                raise ValueError("Binary content")
            if decoded.lstrip().lower().startswith(("<", "#!", "%pdf-")):
                raise ValueError("Not CSV text")
    except (
        ValueError,
        OSError,
        BadZipFile,
        KeyError,
        RuntimeError,
        DefusedXmlException,
        ElementTree.ParseError,
    ):
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "Source bytes do not match the format"
        ) from None
    return ValidatedUpload(
        content=content,
        filename=filename,
        media_type=MEDIA_TYPES[format],
        format=format,
        checksum=hashlib.sha256(content).hexdigest(),
    )


def validate_connected_json(stream: BinaryIO) -> ValidatedUpload:
    content = stream.read(MAX_UPLOAD_BYTES + 1)
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Source payload size is invalid")
    # A connected adapter supplies JSON bytes. Business fields are not parsed here.
    if content.lstrip()[:1] not in (b"{", b"["):
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Source payload is not JSON")
    return ValidatedUpload(
        content=content,
        filename="source.json",
        media_type=MEDIA_TYPES[SourceFormat.JSON],
        format=SourceFormat.JSON,
        checksum=hashlib.sha256(content).hexdigest(),
    )


def _check_workbook_container(content: bytes, format: SourceFormat) -> None:
    with ZipFile(BytesIO(content)) as archive:
        entries = validate_zip_archive(archive)
        names = {entry.filename for entry in entries}
        if len(names) != len(entries):
            raise ValueError("Invalid archive entries")
        if "xl/workbook.xml" not in names:
            raise ValueError("Missing workbook")
        info = archive.getinfo("[Content_Types].xml")
        if info.file_size > MAX_CONTENT_TYPES_BYTES:
            raise ValueError("Content types are too large")
        root = ElementTree.fromstring(archive.read(info))
        expected = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
            if format == SourceFormat.XLSX
            else "application/vnd.ms-excel.sheet.macroEnabled.main+xml"
        )
        if not any(
            node.attrib.get("PartName") == "/xl/workbook.xml"
            and node.attrib.get("ContentType") == expected
            for node in root
        ):
            raise ValueError("Workbook type mismatch")
        if format == SourceFormat.XLSX and any(
            "vbaproject" in name.lower() for name in names
        ):
            raise ValueError("Macro content in XLSX")
        # Do not read worksheet cells, external links, embeddings, or VBA streams.
