"""
Explicit local PDF and image attachments for extract.ai Responses calls.
"""
import base64 as _base64
import hashlib as _hashlib
import json as _json
import re as _re
from dataclasses import dataclass as _dataclass, field as _field
from pathlib import Path as _Path


MAX_ATTACHMENTS = 16
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_RECORD_BYTES = 32 * 1024 * 1024
MAX_BATCH_BYTES = 128 * 1024 * 1024

_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


@_dataclass(frozen=True)
class Attachment:
    id: str
    media_type: str
    data: bytes = _field(repr=False)
    sha256: str
    detail: str = "auto"

    def identity(self) -> dict:
        return {
            "id": self.id,
            "media_type": self.media_type,
            "sha256": self.sha256,
            "detail": self.detail,
        }

    def content(self) -> dict:
        encoded = _base64.b64encode(self.data).decode("ascii")
        data_url = f"data:{self.media_type};base64,{encoded}"
        if self.media_type == "application/pdf":
            return {
                "type": "input_file",
                "filename": f"{self.id}.pdf",
                "file_data": data_url,
            }
        return {
            "type": "input_image",
            "image_url": data_url,
            "detail": self.detail,
        }


@_dataclass(frozen=True)
class PreparedRecord:
    text: str = _field(repr=False)
    attachments: tuple

    def identity(self) -> dict:
        return {
            "text": self.text,
            "attachments": [attachment.identity() for attachment in self.attachments],
        }

    def content(self) -> list:
        parts = []
        if self.text:
            parts.append({"type": "input_text", "text": f"DATA:\n{self.text}"})
        for attachment in self.attachments:
            parts.append({
                "type": "input_text",
                "text": "DATA source: " + _json.dumps({
                    "id": attachment.id,
                    "media_type": attachment.media_type,
                }),
            })
            parts.append(attachment.content())
        return parts


def validate_model(protocol: str) -> None:
    if protocol != "responses":
        raise ValueError("attachments are supported only with protocol='responses'.")


def _matches_format(data: bytes, media_type: str) -> bool:
    if media_type == "application/pdf":
        return data.startswith(b"%PDF-")
    if media_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if media_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    return data.startswith(b"RIFF") and data[8:12] == b"WEBP"


def _check_size(size: int, batch_bytes: int, location: str) -> None:
    if size > MAX_FILE_BYTES:
        raise ValueError(f"{location}: file exceeds the {MAX_FILE_BYTES // (1024 * 1024)} MiB limit.")
    if batch_bytes + size > MAX_BATCH_BYTES:
        raise ValueError("Attachments exceed the 128 MiB batch snapshot limit; use smaller batches.")


def _validate_descriptor(descriptor: dict, location: str, default_id: str) -> dict:
    if not isinstance(descriptor, dict):
        raise TypeError(f"{location}: attachment must be an object with path, id, and optional detail.")
    if set(descriptor) - {"path", "id", "detail"} or "path" not in descriptor:
        raise ValueError(f"{location}: supported attachment fields are path, id, and detail; path is required.")

    source_id = descriptor.get("id", default_id)
    if not isinstance(source_id, str) or not _re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", source_id):
        raise ValueError(
            f"{location}: id must be 1-64 letters, digits, dots, underscores, or hyphens, starting with a letter or digit."
        )

    detail = descriptor.get("detail", "auto")
    if not isinstance(detail, str) or detail not in {"auto", "low", "high"}:
        raise ValueError(f"{location}: detail must be auto, low, or high.")

    path_value = descriptor["path"]
    if not isinstance(path_value, (str, _Path)) or not str(path_value).strip():
        raise TypeError(f"{location}: path must be a non-empty local filesystem path.")
    if _re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", str(path_value)) or str(path_value).startswith("data:"):
        raise ValueError(f"{location}: only local filesystem paths are supported in attachments.")

    return {
        "id": source_id,
        "path": _Path(path_value),
        "detail": detail,
        "detail_provided": "detail" in descriptor,
    }


def _read_snapshot(path: _Path, snapshots: dict, batch_bytes: int, location: str) -> tuple:
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_file():
            raise ValueError(f"{location}: path must reference a regular file.")
        if resolved not in snapshots:
            _check_size(resolved.stat().st_size, batch_bytes, location)
            with resolved.open("rb") as file:
                data = file.read(min(MAX_FILE_BYTES, MAX_BATCH_BYTES - batch_bytes) + 1)
            _check_size(len(data), batch_bytes, location)
            if not data:
                raise ValueError(f"{location}: file is empty.")
            snapshots[resolved] = (data, _hashlib.sha256(data).hexdigest())
            batch_bytes += len(data)
        data, digest = snapshots[resolved]
        return resolved, data, digest, batch_bytes
    except OSError as exc:
        raise ValueError(f"{location}: local file is missing or unreadable; check path and permissions.") from exc


def prepare(rows: list, attachments: list, scalar: bool, format_text) -> list:
    """
    Snapshot attachment bytes once so retries and cache keys use the same content.
    """
    if not isinstance(attachments, list):
        raise TypeError("attachments must be a list of descriptors, or one descriptor list per input record.")

    groups = [attachments] if scalar else attachments
    if len(groups) != len(rows) or any(not isinstance(group, list) for group in groups):
        raise ValueError("Batch attachments must contain one attachment list per input record, in input order.")

    snapshots = {}
    batch_bytes = 0
    prepared = []
    for row_index, (row, group) in enumerate(zip(rows, groups)):
        if len(group) > MAX_ATTACHMENTS:
            raise ValueError(f"Record {row_index}: attachments must contain at most {MAX_ATTACHMENTS} files.")
        ids = set()
        record_bytes = 0
        sources = []
        for attachment_index, descriptor in enumerate(group):
            location = f"Record {row_index}, attachment {attachment_index + 1}"
            validated = _validate_descriptor(descriptor, location, f"source-{attachment_index + 1}")
            if validated["id"] in ids:
                raise ValueError(f"{location}: attachment ids must be unique within each record.")
            ids.add(validated["id"])

            path, data, digest, batch_bytes = _read_snapshot(
                validated["path"],
                snapshots,
                batch_bytes,
                location,
            )
            media_type = _MEDIA_TYPES.get(path.suffix.lower())
            if media_type is None:
                raise ValueError(f"{location}: supported formats are PDF, PNG, JPEG, and WebP.")
            if media_type == "application/pdf" and validated["detail_provided"]:
                raise ValueError(f"{location}: detail applies only to images, not PDF files.")
            if not _matches_format(data, media_type):
                raise ValueError(f"{location}: file contents do not match its PDF/image extension.")

            record_bytes += len(data)
            if record_bytes > MAX_RECORD_BYTES:
                raise ValueError("Attachments exceed the 32 MiB per-record limit; split the document or request.")
            sources.append(Attachment(validated["id"], media_type, data, digest, validated["detail"]))
        prepared.append(PreparedRecord("" if row is None else format_text(row), tuple(sources)) if sources else row)
    return prepared
