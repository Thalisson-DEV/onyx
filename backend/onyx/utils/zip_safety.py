"""Shared archive metadata limits. Never extracts or executes members."""

import zipfile
from pathlib import PurePosixPath

from onyx.configs.app_configs import (
    MAX_ZIP_COMPRESSION_RATIO,
    MAX_ZIP_ENTRIES,
    MAX_ZIP_EXPANDED_SIZE_BYTES,
    MAX_ZIP_FILENAME_LENGTH,
    MAX_ZIP_MEMBER_SIZE_BYTES,
    MAX_ZIP_PATH_DEPTH,
)
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError


def _validate_zip_member_name(
    filename: str, max_filename_length: int, max_path_depth: int
) -> None:
    normalized_name = filename.replace("\\", "/")
    path = PurePosixPath(normalized_name)
    if (
        not normalized_name
        or len(normalized_name) > max_filename_length
        or path.is_absolute()
        or ".." in path.parts
        or "\x00" in normalized_name
    ):
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "ZIP contains an unsafe path")
    if len(path.parts) > max_path_depth:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT,
            "ZIP member exceeds the allowed path depth",
        )


def validate_zip_archive(
    zf: zipfile.ZipFile,
    *,
    max_entries: int = MAX_ZIP_ENTRIES,
    max_expanded_size: int = MAX_ZIP_EXPANDED_SIZE_BYTES,
    max_member_size: int = MAX_ZIP_MEMBER_SIZE_BYTES,
    max_compression_ratio: int = MAX_ZIP_COMPRESSION_RATIO,
    max_filename_length: int = MAX_ZIP_FILENAME_LENGTH,
    max_path_depth: int = MAX_ZIP_PATH_DEPTH,
) -> list[zipfile.ZipInfo]:
    """Validate archive metadata before any member content is read."""
    members = zf.infolist()
    if len(members) > max_entries:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "ZIP contains too many files")

    expanded_size = 0
    for member in members:
        _validate_zip_member_name(member.filename, max_filename_length, max_path_depth)
        if member.is_dir():
            continue
        if member.file_size > max_member_size:
            raise OnyxError(
                OnyxErrorCode.PAYLOAD_TOO_LARGE,
                "ZIP member exceeds the allowed size",
            )

        expanded_size += member.file_size
        if expanded_size > max_expanded_size:
            raise OnyxError(
                OnyxErrorCode.PAYLOAD_TOO_LARGE,
                "ZIP exceeds the allowed expanded size",
            )

        compressed_size = max(member.compress_size, 1)
        if member.file_size / compressed_size > max_compression_ratio:
            raise OnyxError(
                OnyxErrorCode.INVALID_INPUT,
                "ZIP member exceeds the allowed compression ratio",
            )

    return members
