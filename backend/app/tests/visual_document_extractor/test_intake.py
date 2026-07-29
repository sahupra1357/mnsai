from __future__ import annotations

import hashlib
import io
import zipfile

import pytest

from app.visual_document_extractor.intake import (
    SUPPORTED_EXTENSIONS,
    IntakeErrorCode,
    IntakeLimits,
    IntakeValidationError,
    validate_upload,
)


def _pdf_bytes(*, encrypted: bool = False, pages: int = 1) -> bytes:
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    for page_number in range(pages):
        page = document.new_page()
        page.insert_text((72, 72), f"Native text page {page_number + 1}")
    if encrypted:
        content = document.tobytes(
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw="owner-password",
            user_pw="user-password",
        )
    else:
        content = document.tobytes()
    document.close()
    return content


def _openxml_bytes(
    kind: str, *, slides: int = 1, extra: dict[str, bytes] | None = None
) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            (
                b'<?xml version="1.0"?>'
                b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'
            ),
        )
        archive.writestr(
            "_rels/.rels",
            (
                b'<?xml version="1.0"?>'
                b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
            ),
        )
        if kind == "docx":
            archive.writestr("word/document.xml", b"<document><body/></document>")
        elif kind == "pptx":
            archive.writestr("ppt/presentation.xml", b"<presentation/>")
            for page_number in range(1, slides + 1):
                archive.writestr(f"ppt/slides/slide{page_number}.xml", b"<slide/>")
        else:
            raise ValueError(kind)
        for name, value in (extra or {}).items():
            archive.writestr(name, value)
    return buffer.getvalue()


def _image_bytes(image_format: str) -> bytes:
    image_module = pytest.importorskip("PIL.Image")
    image = image_module.new("RGB", (3, 2), color=(20, 80, 140))
    buffer = io.BytesIO()
    image.save(buffer, format=image_format)
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("filename", "image_format", "media_type"),
    [
        ("page.png", "PNG", "image/png"),
        ("page.jpg", "JPEG", "image/jpeg"),
        ("page.jpeg", "JPEG", "image/jpeg"),
        ("page.tif", "TIFF", "image/tiff"),
        ("page.tiff", "TIFF", "image/tiff"),
        ("page.bmp", "BMP", "image/bmp"),
        ("page.gif", "GIF", "image/gif"),
        ("page.webp", "WEBP", "image/webp"),
    ],
)
def test_accepts_supported_images(
    filename: str, image_format: str, media_type: str
) -> None:
    source = validate_upload(filename, _image_bytes(image_format))

    assert source.metadata.media_type == media_type
    assert source.metadata.page_count == 1
    assert source.metadata.source_sha256 == hashlib.sha256(source.content).hexdigest()


def test_accepts_pdf_and_reports_real_page_count() -> None:
    source = validate_upload("report.PDF", _pdf_bytes(pages=2))

    assert source.extension == ".pdf"
    assert source.metadata.page_count == 2
    assert source.metadata.media_type == "application/pdf"


def test_accepts_docx_and_pptx_packages() -> None:
    document = validate_upload("notes.docx", _openxml_bytes("docx"))
    presentation = validate_upload("briefing.pptx", _openxml_bytes("pptx", slides=3))

    assert document.metadata.page_count == 1
    assert "provisional" in document.warnings[0]
    assert presentation.metadata.page_count == 3


def test_uses_safe_basename_without_trusting_path() -> None:
    source = validate_upload(r"C:\fakepath\quarterly report.pdf", _pdf_bytes())

    assert source.metadata.source_name == "quarterly report.pdf"


def test_rejects_extension_and_magic_mismatch() -> None:
    with pytest.raises(IntakeValidationError) as caught:
        validate_upload("disguised.pdf", _image_bytes("PNG"))

    assert caught.value.code == IntakeErrorCode.FORMAT_MISMATCH
    assert "does not match" in caught.value.safe_message


def test_rejects_docx_pptx_package_mismatch() -> None:
    with pytest.raises(IntakeValidationError) as caught:
        validate_upload("disguised.docx", _openxml_bytes("pptx"))

    assert caught.value.code == IntakeErrorCode.FORMAT_MISMATCH


def test_rejects_empty_unsupported_and_corrupt_inputs() -> None:
    with pytest.raises(IntakeValidationError) as empty:
        validate_upload("empty.pdf", b"")
    assert empty.value.code == IntakeErrorCode.EMPTY_FILE

    with pytest.raises(IntakeValidationError) as unsupported:
        validate_upload("payload.exe", b"MZ")
    assert unsupported.value.code == IntakeErrorCode.UNSUPPORTED_FORMAT
    assert all(
        extension in unsupported.value.safe_message
        for extension in SUPPORTED_EXTENSIONS
    )

    with pytest.raises(IntakeValidationError) as corrupt_pdf:
        validate_upload("broken.pdf", b"%PDF-1.7\nmissing end marker")
    assert corrupt_pdf.value.code == IntakeErrorCode.CORRUPT_FILE

    with pytest.raises(IntakeValidationError) as corrupt_png:
        validate_upload("broken.png", b"\x89PNG\r\n\x1a\ntruncated")
    assert corrupt_png.value.code == IntakeErrorCode.CORRUPT_FILE


def test_rejects_encrypted_pdf() -> None:
    with pytest.raises(IntakeValidationError) as caught:
        validate_upload("locked.pdf", _pdf_bytes(encrypted=True))

    assert caught.value.code == IntakeErrorCode.ENCRYPTED_FILE
    assert "Encrypted PDFs" in caught.value.safe_message


def test_rejects_encrypted_or_legacy_binary_office_container() -> None:
    ole_header = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + (b"\x00" * 504)

    with pytest.raises(IntakeValidationError) as caught:
        validate_upload("locked.docx", ole_header)

    assert caught.value.code == IntakeErrorCode.ENCRYPTED_FILE
    assert "unencrypted Open XML" in caught.value.safe_message


def test_rejects_page_limit() -> None:
    with pytest.raises(IntakeValidationError) as caught:
        validate_upload(
            "many-pages.pdf",
            _pdf_bytes(pages=2),
            limits=IntakeLimits(max_pages=1),
        )

    assert caught.value.code == IntakeErrorCode.TOO_MANY_PAGES


def test_rejects_image_pixel_limit() -> None:
    with pytest.raises(IntakeValidationError) as caught:
        validate_upload(
            "large.png",
            _image_bytes("PNG"),
            limits=IntakeLimits(max_image_pixels=5),
        )

    assert caught.value.code == IntakeErrorCode.IMAGE_TOO_LARGE


class _RecordingStream(io.BytesIO):
    def __init__(self, content: bytes) -> None:
        super().__init__(content)
        self.requests: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.requests.append(size)
        return super().read(size)


def test_stream_read_is_bounded_and_stops_after_limit() -> None:
    stream = _RecordingStream(b"x" * 101)

    with pytest.raises(IntakeValidationError) as caught:
        validate_upload(
            "large.pdf",
            stream,
            limits=IntakeLimits(max_upload_bytes=100, read_chunk_bytes=16),
        )

    assert caught.value.code == IntakeErrorCode.FILE_TOO_LARGE
    assert max(stream.requests) <= 16
    assert stream.tell() == 101


def test_rejects_archive_expansion_and_unsafe_paths() -> None:
    compressed = _openxml_bytes("docx", extra={"word/large.xml": b"A" * 10_000})
    with pytest.raises(IntakeValidationError) as expanded:
        validate_upload(
            "large.docx",
            compressed,
            limits=IntakeLimits(
                max_archive_expanded_bytes=1024,
                max_archive_compression_ratio=10_000,
            ),
        )
    assert expanded.value.code == IntakeErrorCode.ARCHIVE_TOO_LARGE

    unsafe = _openxml_bytes("docx", extra={"../outside.xml": b"unsafe"})
    with pytest.raises(IntakeValidationError) as traversal:
        validate_upload("unsafe.docx", unsafe)
    assert traversal.value.code == IntakeErrorCode.UNSAFE_ARCHIVE


def test_rejects_office_compression_bomb_ratio() -> None:
    compressed = _openxml_bytes("docx", extra={"word/repetitive.xml": b"A" * 20_000})

    with pytest.raises(IntakeValidationError) as caught:
        validate_upload(
            "compressed.docx",
            compressed,
            limits=IntakeLimits(max_archive_compression_ratio=10),
        )

    assert caught.value.code == IntakeErrorCode.UNSAFE_ARCHIVE
