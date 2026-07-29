from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from app.visual_document_extractor.preview import (
    PreviewConfig,
    PreviewError,
    PreviewErrorCode,
    convert_office_to_pdf,
    render_preview,
)


def _pdf_bytes() -> bytes:
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    page = document.new_page(width=200, height=100)
    page.insert_text((20, 50), "stable preview")
    content = document.tobytes()
    document.close()
    return content


def _png_bytes() -> bytes:
    image_module = pytest.importorskip("PIL.Image")
    image = image_module.new("RGB", (40, 20), (240, 10, 20))
    output = __import__("io").BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_pdf_preview_is_stable_and_page_oriented() -> None:
    source = _pdf_bytes()
    first = render_preview(source, "application/pdf", 1)
    second = render_preview(source, "application/pdf", 1)

    assert first.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert (first.width, first.height) == (400, 200)
    assert first.content == second.content
    assert first.content_sha256 == second.content_sha256


def test_image_preview_is_stable() -> None:
    source = _png_bytes()
    first = render_preview(source, "image/png", 1)
    second = render_preview(source, "image/png", 1)

    assert (first.width, first.height) == (40, 20)
    assert first.content == second.content


@pytest.mark.parametrize("page_number", [0, 2])
def test_page_bounds_are_actionable(page_number: int) -> None:
    with pytest.raises(PreviewError) as caught:
        render_preview(_pdf_bytes(), "application/pdf", page_number)
    assert caught.value.code == PreviewErrorCode.INVALID_PAGE


def test_office_converter_unavailable() -> None:
    config = PreviewConfig(office_binary="/definitely/missing/soffice")
    with pytest.raises(PreviewError) as caught:
        convert_office_to_pdf(
            b"package",
            source_name="report.docx",
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            config=config,
        )
    assert caught.value.code == PreviewErrorCode.UNAVAILABLE


def test_office_timeout_cleans_temporary_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    created: list[Path] = []

    class ControlledTemporaryDirectory:
        def __init__(self, prefix: str) -> None:
            self.path = tmp_path / f"{prefix}controlled"
            created.append(self.path)

        def __enter__(self) -> str:
            self.path.mkdir()
            return str(self.path)

        def __exit__(self, *_args: object) -> None:
            import shutil

            shutil.rmtree(self.path)

    def timeout(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(cmd=["soffice"], timeout=0.01)

    monkeypatch.setattr(
        "app.visual_document_extractor.preview.tempfile.TemporaryDirectory",
        ControlledTemporaryDirectory,
    )
    monkeypatch.setattr("app.visual_document_extractor.preview._run_office", timeout)
    with pytest.raises(PreviewError) as caught:
        convert_office_to_pdf(
            b"package",
            source_name="../../unsafe.pptx",
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "presentationml.presentation"
            ),
            config=PreviewConfig(office_binary="soffice", office_timeout_seconds=0.01),
        )
    assert caught.value.code == PreviewErrorCode.CONVERSION_TIMEOUT
    assert created and not created[0].exists()


def test_office_failure_does_not_expose_converter_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "document-derived-secret"

    def failed(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            args=["soffice"], returncode=1, stdout=b"", stderr=secret.encode()
        )

    monkeypatch.setattr("app.visual_document_extractor.preview._run_office", failed)
    with pytest.raises(PreviewError) as caught:
        convert_office_to_pdf(
            b"package",
            source_name="report.docx",
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            config=PreviewConfig(office_binary="soffice"),
        )
    assert caught.value.code == PreviewErrorCode.CONVERSION_FAILED
    assert secret not in caught.value.safe_message
