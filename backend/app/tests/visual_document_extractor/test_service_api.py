from __future__ import annotations

import io
import uuid
import zipfile

import pytest

from app.api.routes import document_extractions
from app.visual_document_extractor.adapters import PaddleOCRAdapter
from app.visual_document_extractor.intake import IntakeValidationError
from app.visual_document_extractor.models import (
    AdapterResult,
    AttemptStatus,
    ExtractedElement,
    ExtractionAttempt,
    PageReviewRequest,
    ReprocessRequest,
    ReviewElementUpdate,
)
from app.visual_document_extractor.routing import ExtractionRouter
from app.visual_document_extractor.service import (
    DocumentExtractionService,
    ServiceLimits,
)
from app.visual_document_extractor.store import InMemoryDocumentStore

OWNER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _png_bytes() -> bytes:
    image_module = pytest.importorskip("PIL.Image")
    image = image_module.new("RGB", (20, 10), color=(255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _docx_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", b"<Types/>")
        archive.writestr("_rels/.rels", b"<Relationships/>")
        archive.writestr("word/document.xml", b"<document><body/></document>")
    return buffer.getvalue()


def _pdf_with_pages(count: int) -> bytes:
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    for _ in range(count):
        document.new_page()
    content = document.tobytes()
    document.close()
    return content


def _successful_result(_page: object) -> AdapterResult:
    return AdapterResult(
        attempt=ExtractionAttempt(
            parser="paddleocr",
            version="test",
            status=AttemptStatus.SUCCEEDED,
            confidence=0.99,
        ),
        elements=[
            ExtractedElement(
                element_id="page-1-block-1",
                text="Original extraction",
                reading_order=0,
                confidence=0.99,
                confidence_source="parser",
            )
        ],
    )


def make_service() -> DocumentExtractionService:
    adapter = PaddleOCRAdapter(executor=_successful_result, version="test")
    return DocumentExtractionService(
        store=InMemoryDocumentStore(),
        router=ExtractionRouter([adapter]),
    )


def test_identical_upload_reuses_reviewable_result_and_bounding_elements() -> None:
    service = make_service()
    content = _png_bytes()
    first = service.ingest(
        owner_id=OWNER_ID,
        source_name="scan.png",
        content=content,
    )
    service.review_page(
        first.document_id,
        1,
        OWNER_ID,
        PageReviewRequest(
            action="save",
            elements=[
                ReviewElementUpdate(
                    element_id="page-1-block-1",
                    reviewed_text="Corrected extraction",
                )
            ],
        ),
    )

    reused = service.ingest(
        owner_id=OWNER_ID,
        source_name="renamed-same-content.png",
        content=content,
    )

    assert reused.reused_extraction is True
    assert reused.document_id == first.document_id
    assert reused.pages[0].elements[0].text == "Original extraction"
    assert reused.pages[0].elements[0].reviewed_text == "Corrected extraction"
    assert reused.pages[0].elements[0].element_id == "page-1-block-1"


def test_modal_backend_changes_cache_identity_and_exposes_remote_parsers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = make_service()
    local_fingerprint = service._extraction_fingerprint(None)
    monkeypatch.setattr(service, "_modal_configured", lambda: True)

    modal_fingerprint = service._extraction_fingerprint(None)
    capabilities = service.capabilities()
    paddleocr = next(
        item for item in capabilities.adapters if item.name == "paddleocr"
    )

    assert modal_fingerprint != local_fingerprint
    assert capabilities.execution_backend == "modal"
    assert paddleocr.available is True
    assert paddleocr.version == "3.7.0"
    assert paddleocr.reason == "Executed remotely on Modal"


def test_failed_reprocess_remains_manual_review_required() -> None:
    def failed_result(_page: object) -> AdapterResult:
        return AdapterResult(
            attempt=ExtractionAttempt(
                parser="paddleocr",
                version="test",
                status=AttemptStatus.FAILED,
                error_code="fixture_failure",
            )
        )

    service = DocumentExtractionService(
        store=InMemoryDocumentStore(),
        router=ExtractionRouter(
            [PaddleOCRAdapter(executor=failed_result, version="test")]
        ),
    )
    document = service.ingest(
        owner_id=OWNER_ID,
        source_name="scan.png",
        content=_png_bytes(),
    )

    page = service.reprocess_page(
        document.document_id,
        1,
        OWNER_ID,
        ReprocessRequest(reason="forced failure"),
    )

    assert page.page_status.value == "manual_review_required"


def test_docx_conversion_stabilizes_multi_page_count(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.visual_document_extractor.service.convert_office_to_pdf",
        lambda *_args, **_kwargs: _pdf_with_pages(3),
    )
    service = make_service()

    document = service.ingest(
        owner_id=OWNER_ID,
        source_name="multi-page.docx",
        content=_docx_bytes(),
    )

    assert document.source.page_count == 3
    assert [page.page_number for page in document.pages] == [1, 2, 3]


def test_docx_conversion_enforces_stabilized_page_limit(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.visual_document_extractor.service.convert_office_to_pdf",
        lambda *_args, **_kwargs: _pdf_with_pages(3),
    )
    service = make_service()
    service.limits = ServiceLimits(
        max_upload_bytes=10_000_000,
        max_pages=2,
        max_image_pixels=1_000_000,
        parser_timeout_seconds=5,
    )

    with pytest.raises(IntakeValidationError) as caught:
        service.ingest(
            owner_id=OWNER_ID,
            source_name="too-many-pages.docx",
            content=_docx_bytes(),
        )

    assert caught.value.code.value == "too_many_pages"


def test_service_preserves_original_text_and_audits_review() -> None:
    service = make_service()
    document = service.ingest(
        owner_id=OWNER_ID,
        source_name="scan.png",
        content=_png_bytes(),
    )

    page = service.review_page(
        document.document_id,
        1,
        OWNER_ID,
        PageReviewRequest(
            action="approve",
            elements=[
                ReviewElementUpdate(
                    element_id="page-1-block-1",
                    reviewed_text="Human correction",
                )
            ],
        ),
    )

    assert page.elements[0].text == "Original extraction"
    assert page.elements[0].reviewed_text == "Human correction"
    assert page.review.status.value == "approved"
    assert page.audit_events[-1].event_type == "review_approve"

    reprocessed = service.reprocess_page(
        document.document_id,
        1,
        OWNER_ID,
        ReprocessRequest(
            parser="paddleocr",
            reason="verify corrected-history preservation",
        ),
    )
    preserved = next(
        snapshot
        for snapshot in reprocessed.extraction_history
        if snapshot.reason == "pre_reprocess_review_state"
    )
    assert preserved.elements[0].text == "Original extraction"
    assert preserved.elements[0].reviewed_text == "Human correction"
    assert reprocessed.selected_parser is not None
    assert reprocessed.selected_parser.name == "paddleocr"
    assert reprocessed.audit_events[-1].event_type == "page_reprocessed"
    assert reprocessed.audit_events[-1].details["parser"] == "paddleocr"


def test_authenticated_api_upload_get_source_and_reject_invalid(
    client, monkeypatch
) -> None:
    service = make_service()
    monkeypatch.setattr(document_extractions, "get_service", lambda: service)

    response = client.post(
        "/api/v1/document-extractions",
        files={"file": ("scan.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["source"]["media_type"] == "image/png"
    assert body["pages"][0]["selected_parser"]["name"] == "paddleocr"
    assert body["pages"][0]["confidence"] == pytest.approx(0.99)
    assert body["pages"][0]["confidence_source"] == "paddleocr:page_mean"

    document_id = body["document_id"]
    exported = client.get(
        f"/api/v1/document-extractions/{document_id}/export"
    )
    assert exported.status_code == 200
    assert exported.headers["content-type"] == "application/json"
    assert exported.headers["content-disposition"].startswith("attachment;")
    assert exported.json() == {
        "page_1": {
            "sections": [
                {"type": "paragraph", "text": "Original extraction"}
            ]
        }
    }

    source = client.get(f"/api/v1/document-extractions/{document_id}/source")
    assert source.status_code == 200
    assert source.content == _png_bytes()
    assert source.headers["cache-control"] == "private, no-store"

    preview = client.get(
        f"/api/v1/document-extractions/{document_id}/pages/1/preview"
    )
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "image/png"
    assert preview.headers["x-content-type-options"] == "nosniff"
    assert preview.content.startswith(b"\x89PNG\r\n\x1a\n")

    invalid = client.post(
        "/api/v1/document-extractions",
        files={"file": ("not-an-image.png", b"plain text", "image/png")},
    )
    assert invalid.status_code == 400
    assert "does not match" in invalid.json()["detail"]

    invalid_parser = client.post(
        "/api/v1/document-extractions",
        data={"parser": "not-a-parser"},
        files={"file": ("scan.png", _png_bytes(), "image/png")},
    )
    assert invalid_parser.status_code == 400
    assert "Unsupported parser override" in invalid_parser.json()["detail"]

    deleted = client.delete(f"/api/v1/document-extractions/{document_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/document-extractions/{document_id}").status_code == 404
