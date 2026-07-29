"""Bounded, parser-independent validation for uploaded source documents.

This module deliberately uses only the standard library at import time. Optional
format libraries are loaded inside validation probes so a missing heavyweight
dependency cannot prevent the application from starting.
"""

from __future__ import annotations

import hashlib
import importlib
import io
import re
import zipfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath
from typing import BinaryIO

from .models import SourceMetadata


class IntakeErrorCode(str, Enum):
    EMPTY_FILE = "empty_file"
    INVALID_FILENAME = "invalid_filename"
    UNSUPPORTED_FORMAT = "unsupported_format"
    FORMAT_MISMATCH = "format_mismatch"
    FILE_TOO_LARGE = "file_too_large"
    TOO_MANY_PAGES = "too_many_pages"
    CORRUPT_FILE = "corrupt_file"
    ENCRYPTED_FILE = "encrypted_file"
    UNSAFE_ARCHIVE = "unsafe_archive"
    ARCHIVE_TOO_LARGE = "archive_too_large"
    IMAGE_TOO_LARGE = "image_too_large"


class IntakeValidationError(ValueError):
    """A validation failure safe to expose to an upload client."""

    def __init__(self, code: IntakeErrorCode, safe_message: str) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


@dataclass(frozen=True, slots=True)
class IntakeLimits:
    max_upload_bytes: int = 50 * 1024 * 1024
    read_chunk_bytes: int = 64 * 1024
    max_pages: int = 500
    max_archive_entries: int = 10_000
    max_archive_expanded_bytes: int = 250 * 1024 * 1024
    max_archive_compression_ratio: float = 250.0
    max_image_pixels: int = 100_000_000

    def __post_init__(self) -> None:
        if self.max_upload_bytes < 1:
            raise ValueError("max_upload_bytes must be positive")
        if self.read_chunk_bytes < 1:
            raise ValueError("read_chunk_bytes must be positive")
        if self.max_pages < 1:
            raise ValueError("max_pages must be positive")
        if self.max_archive_entries < 1:
            raise ValueError("max_archive_entries must be positive")
        if self.max_archive_expanded_bytes < 1:
            raise ValueError("max_archive_expanded_bytes must be positive")
        if self.max_archive_compression_ratio <= 0:
            raise ValueError("max_archive_compression_ratio must be positive")
        if self.max_image_pixels < 1:
            raise ValueError("max_image_pixels must be positive")


@dataclass(frozen=True, slots=True)
class ValidatedSource:
    """Immutable source bytes and metadata accepted by downstream storage."""

    content: bytes = field(repr=False)
    metadata: SourceMetadata
    extension: str
    warnings: tuple[str, ...] = ()


_EXTENSION_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    ".pptx": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ),
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".bmp": "image/bmp",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

SUPPORTED_EXTENSIONS = tuple(sorted(_EXTENSION_MEDIA_TYPES))


def validate_upload(
    source_name: str,
    source: bytes | bytearray | memoryview | BinaryIO,
    *,
    limits: IntakeLimits | None = None,
) -> ValidatedSource:
    """Read at most the configured limit and validate extension plus content.

    The returned bytes are immutable. No parser receives the caller-owned stream
    or a mutable upload buffer.
    """

    active_limits = limits or IntakeLimits()
    clean_name, extension = _validate_source_name(source_name)
    content, checksum = _read_bounded(source, active_limits)
    expected_media_type = _EXTENSION_MEDIA_TYPES[extension]
    detected_kind = _detect_kind(content)

    warnings: list[str] = []
    if extension in {".docx", ".pptx"}:
        if detected_kind == "ole":
            raise IntakeValidationError(
                IntakeErrorCode.ENCRYPTED_FILE,
                "The Office file is encrypted or uses a legacy binary format; "
                "upload an unencrypted Open XML document.",
            )
        if detected_kind != "zip":
            _raise_mismatch(extension, detected_kind)
        package_kind, page_count, package_warnings = _validate_openxml(
            content, active_limits
        )
        if package_kind != extension[1:]:
            _raise_mismatch(extension, package_kind)
        warnings.extend(package_warnings)
    else:
        expected_kind = {
            ".pdf": "pdf",
            ".png": "png",
            ".jpg": "jpeg",
            ".jpeg": "jpeg",
            ".tif": "tiff",
            ".tiff": "tiff",
            ".bmp": "bmp",
            ".gif": "gif",
            ".webp": "webp",
        }[extension]
        if detected_kind != expected_kind:
            _raise_mismatch(extension, detected_kind)
        if expected_kind == "pdf":
            page_count = _validate_pdf(content)
        else:
            page_count = _validate_image(content, expected_kind, active_limits)

    if page_count > active_limits.max_pages:
        raise IntakeValidationError(
            IntakeErrorCode.TOO_MANY_PAGES,
            f"The document has {page_count} pages; the limit is "
            f"{active_limits.max_pages}.",
        )

    metadata = SourceMetadata(
        source_name=clean_name,
        source_sha256=checksum,
        media_type=expected_media_type,
        size_bytes=len(content),
        page_count=page_count,
    )
    return ValidatedSource(
        content=content,
        metadata=metadata,
        extension=extension,
        warnings=tuple(warnings),
    )


def _validate_source_name(source_name: str) -> tuple[str, str]:
    if not isinstance(source_name, str) or not source_name.strip():
        raise IntakeValidationError(
            IntakeErrorCode.INVALID_FILENAME, "A source filename is required."
        )
    if "\x00" in source_name:
        raise IntakeValidationError(
            IntakeErrorCode.INVALID_FILENAME,
            "The source filename contains an invalid character.",
        )
    clean_name = PurePosixPath(source_name.replace("\\", "/")).name.strip()
    if clean_name in {"", ".", ".."}:
        raise IntakeValidationError(
            IntakeErrorCode.INVALID_FILENAME, "A valid source filename is required."
        )
    dot = clean_name.rfind(".")
    extension = clean_name[dot:].lower() if dot >= 0 else ""
    if extension not in _EXTENSION_MEDIA_TYPES:
        supported = ", ".join(SUPPORTED_EXTENSIONS)
        raise IntakeValidationError(
            IntakeErrorCode.UNSUPPORTED_FORMAT,
            f"Unsupported file type. Supported extensions: {supported}.",
        )
    return clean_name, extension


def _read_bounded(
    source: bytes | bytearray | memoryview | BinaryIO, limits: IntakeLimits
) -> tuple[bytes, str]:
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    total = 0

    if isinstance(source, bytes | bytearray | memoryview):
        raw = bytes(source)
        if not raw:
            raise IntakeValidationError(
                IntakeErrorCode.EMPTY_FILE, "The uploaded file is empty."
            )
        if len(raw) > limits.max_upload_bytes:
            raise IntakeValidationError(
                IntakeErrorCode.FILE_TOO_LARGE,
                f"The uploaded file exceeds the {limits.max_upload_bytes}-byte limit.",
            )
        digest.update(raw)
        return raw, digest.hexdigest()

    read = getattr(source, "read", None)
    if not callable(read):
        raise TypeError("source must be bytes or a binary file-like object")

    while True:
        remaining = limits.max_upload_bytes - total
        request_size = min(limits.read_chunk_bytes, remaining + 1)
        chunk = read(request_size)
        if chunk in (b"", None):
            break
        if not isinstance(chunk, bytes | bytearray | memoryview):
            raise TypeError("source must be opened in binary mode")
        immutable_chunk = bytes(chunk)
        total += len(immutable_chunk)
        if total > limits.max_upload_bytes:
            raise IntakeValidationError(
                IntakeErrorCode.FILE_TOO_LARGE,
                f"The uploaded file exceeds the {limits.max_upload_bytes}-byte limit.",
            )
        chunks.append(immutable_chunk)
        digest.update(immutable_chunk)

    if total == 0:
        raise IntakeValidationError(
            IntakeErrorCode.EMPTY_FILE, "The uploaded file is empty."
        )
    return b"".join(chunks), digest.hexdigest()


def _detect_kind(content: bytes) -> str:
    head = content[:1024]
    if head.lstrip(b"\xef\xbb\xbf\x00\t\r\n ")[:5] == b"%PDF-":
        return "pdf"
    if content.startswith(b"PK\x03\x04"):
        return "zip"
    if content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "ole"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if content.startswith((b"II*\x00", b"MM\x00*")):
        return "tiff"
    if content.startswith(b"BM"):
        return "bmp"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "webp"
    return "unknown"


def _raise_mismatch(extension: str, detected_kind: str) -> None:
    detected = detected_kind if detected_kind != "unknown" else "unknown content"
    raise IntakeValidationError(
        IntakeErrorCode.FORMAT_MISMATCH,
        f"The {extension} extension does not match the detected {detected} format.",
    )


def _validate_pdf(content: bytes) -> int:
    # A valid PDF has a header near the beginning and an EOF marker near the end.
    if b"%%EOF" not in content[-4096:]:
        raise IntakeValidationError(
            IntakeErrorCode.CORRUPT_FILE,
            "The PDF is incomplete or corrupt (missing end marker).",
        )

    try:
        fitz = importlib.import_module("fitz")
    except ImportError:
        # Conservative standard-library fallback when the configured PDF probe is
        # not installed. It does not claim full parser-level validation.
        if re.search(rb"/Encrypt\b", content):
            raise IntakeValidationError(
                IntakeErrorCode.ENCRYPTED_FILE,
                "Encrypted PDFs are not supported.",
            )
        page_count = len(re.findall(rb"/Type\s*/Page\b", content))
        return max(page_count, 1)

    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise IntakeValidationError(
            IntakeErrorCode.CORRUPT_FILE,
            "The PDF could not be opened because it is corrupt or malformed.",
        ) from exc

    try:
        if bool(document.needs_pass):
            raise IntakeValidationError(
                IntakeErrorCode.ENCRYPTED_FILE,
                "Encrypted PDFs are not supported.",
            )
        page_count = int(document.page_count)
        if page_count < 1:
            raise IntakeValidationError(
                IntakeErrorCode.CORRUPT_FILE,
                "The PDF does not contain any pages.",
            )
        return page_count
    finally:
        document.close()


def _validate_openxml(
    content: bytes, limits: IntakeLimits
) -> tuple[str, int, tuple[str, ...]]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except (zipfile.BadZipFile, OSError) as exc:
        raise IntakeValidationError(
            IntakeErrorCode.CORRUPT_FILE,
            "The Office document is not a valid Open XML package.",
        ) from exc

    warnings: list[str] = []
    try:
        entries = archive.infolist()
        if len(entries) > limits.max_archive_entries:
            raise IntakeValidationError(
                IntakeErrorCode.UNSAFE_ARCHIVE,
                "The Office document contains too many archive entries.",
            )

        names: set[str] = set()
        expanded_bytes = 0
        for entry in entries:
            name = entry.filename
            normalized = PurePosixPath(name.replace("\\", "/"))
            if (
                not name
                or name.startswith(("/", "\\"))
                or "\\" in name
                or ".." in normalized.parts
            ):
                raise IntakeValidationError(
                    IntakeErrorCode.UNSAFE_ARCHIVE,
                    "The Office document contains an unsafe archive path.",
                )
            if name in names:
                raise IntakeValidationError(
                    IntakeErrorCode.UNSAFE_ARCHIVE,
                    "The Office document contains duplicate archive entries.",
                )
            names.add(name)
            if entry.flag_bits & 0x1:
                raise IntakeValidationError(
                    IntakeErrorCode.ENCRYPTED_FILE,
                    "Encrypted Office documents are not supported.",
                )
            if entry.is_dir():
                continue
            expanded_bytes += entry.file_size
            if expanded_bytes > limits.max_archive_expanded_bytes:
                raise IntakeValidationError(
                    IntakeErrorCode.ARCHIVE_TOO_LARGE,
                    "The expanded Office document exceeds the configured limit.",
                )
            if entry.file_size:
                ratio = entry.file_size / max(entry.compress_size, 1)
                if ratio > limits.max_archive_compression_ratio:
                    raise IntakeValidationError(
                        IntakeErrorCode.UNSAFE_ARCHIVE,
                        "The Office document contains an unsafe compression ratio.",
                    )

        required_common = {"[Content_Types].xml", "_rels/.rels"}
        if not required_common.issubset(names):
            raise IntakeValidationError(
                IntakeErrorCode.CORRUPT_FILE,
                "The Office document is missing required package metadata.",
            )

        has_word = "word/document.xml" in names
        has_presentation = "ppt/presentation.xml" in names
        if has_word == has_presentation:
            raise IntakeValidationError(
                IntakeErrorCode.CORRUPT_FILE,
                "The Office package type is missing or ambiguous.",
            )

        corrupt_member = archive.testzip()
        if corrupt_member is not None:
            raise IntakeValidationError(
                IntakeErrorCode.CORRUPT_FILE,
                "The Office document contains a corrupt archive entry.",
            )

        content_types = archive.read("[Content_Types].xml")
        if b"macroEnabled" in content_types:
            raise IntakeValidationError(
                IntakeErrorCode.FORMAT_MISMATCH,
                "Macro-enabled Office packages are not accepted as DOCX or PPTX.",
            )

        if has_word:
            warnings.append(
                "DOCX page count is provisional until stable preview rendering."
            )
            return "docx", 1, tuple(warnings)

        slide_pattern = re.compile(r"^ppt/slides/slide[1-9][0-9]*\.xml$")
        page_count = sum(bool(slide_pattern.match(name)) for name in names)
        if page_count < 1:
            raise IntakeValidationError(
                IntakeErrorCode.CORRUPT_FILE,
                "The presentation does not contain any slides.",
            )
        return "pptx", page_count, tuple(warnings)
    except (KeyError, RuntimeError, zipfile.BadZipFile) as exc:
        raise IntakeValidationError(
            IntakeErrorCode.CORRUPT_FILE,
            "The Office document is corrupt or unreadable.",
        ) from exc
    finally:
        archive.close()


def _validate_image(content: bytes, expected_kind: str, limits: IntakeLimits) -> int:
    _validate_image_structure(content, expected_kind)

    try:
        image_module = importlib.import_module("PIL.Image")
    except ImportError:
        return 1

    try:
        with image_module.open(io.BytesIO(content)) as image:
            detected = str(image.format or "").lower()
            aliases = {"jpg": "jpeg", "tif": "tiff"}
            detected = aliases.get(detected, detected)
            if detected != expected_kind:
                _raise_mismatch(f".{expected_kind}", detected)
            page_count = int(getattr(image, "n_frames", 1))
            total_pixels = 0
            for frame_number in range(page_count):
                image.seek(frame_number)
                width, height = image.size
                total_pixels += int(width) * int(height)
                if total_pixels > limits.max_image_pixels:
                    raise IntakeValidationError(
                        IntakeErrorCode.IMAGE_TOO_LARGE,
                        "The image contains more pixels than the configured limit.",
                    )
            image.verify()
    except IntakeValidationError:
        raise
    except Exception as exc:
        raise IntakeValidationError(
            IntakeErrorCode.CORRUPT_FILE,
            "The image is corrupt or unreadable.",
        ) from exc
    return max(page_count, 1)


def _validate_image_structure(content: bytes, kind: str) -> None:
    valid = True
    if kind == "png":
        valid = len(content) >= 20 and b"IEND" in content[-32:]
    elif kind == "jpeg":
        valid = len(content) >= 4 and content.endswith(b"\xff\xd9")
    elif kind == "tiff":
        byte_order = content[:2]
        first_ifd = (
            int.from_bytes(content[4:8], "little" if byte_order == b"II" else "big")
            if len(content) >= 8
            else 0
        )
        valid = len(content) >= 8 and 0 < first_ifd < len(content)
    elif kind == "bmp":
        declared_size = (
            int.from_bytes(content[2:6], "little") if len(content) >= 6 else 0
        )
        pixel_offset = (
            int.from_bytes(content[10:14], "little") if len(content) >= 14 else 0
        )
        valid = (
            len(content) >= 26
            and declared_size <= len(content)
            and 14 <= pixel_offset < len(content)
        )
    elif kind == "webp":
        declared_payload = (
            int.from_bytes(content[4:8], "little") if len(content) >= 12 else -1
        )
        valid = (
            len(content) >= 20
            and declared_payload + 8 <= len(content)
            and content[12:16] in {b"VP8 ", b"VP8L", b"VP8X"}
        )
    elif kind == "gif":
        valid = len(content) >= 14 and content.endswith(b";")
    if not valid:
        raise IntakeValidationError(
            IntakeErrorCode.CORRUPT_FILE,
            f"The {kind.upper()} image is incomplete or corrupt.",
        )
