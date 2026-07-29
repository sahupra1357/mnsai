import json
import uuid
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status

from app.api.deps import CurrentUser
from app.core.config import settings
from app.visual_document_extractor.export import document_content
from app.visual_document_extractor.intake import IntakeValidationError
from app.visual_document_extractor.models import (
    CapabilityResponse,
    DocumentResult,
    PageResult,
    PageReviewRequest,
    ReprocessRequest,
)
from app.visual_document_extractor.preview import (
    PreviewConfig,
    PreviewError,
    PreviewErrorCode,
    render_preview,
)
from app.visual_document_extractor.service import (
    DocumentExtractionService,
    InvalidPageError,
    InvalidParserOverrideError,
    InvalidReviewTransitionError,
    extraction_service,
)
from app.visual_document_extractor.store import (
    ConcurrentDocumentUpdateError,
    DocumentNotFoundError,
    SourceNotFoundError,
    SqlDocumentStore,
    SqlPreviewArtifactCache,
)

router = APIRouter(
    prefix="/document-extractions",
    tags=["document-extractions"],
)


def get_service() -> DocumentExtractionService:
    return extraction_service


@router.get("/capabilities", response_model=CapabilityResponse)
def get_capabilities(current_user: CurrentUser) -> CapabilityResponse:
    del current_user
    return get_service().capabilities()


@router.post("", response_model=DocumentResult, status_code=status.HTTP_201_CREATED)
async def create_document_extraction(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    parser: str | None = Form(default=None),
) -> DocumentResult:
    service = get_service()
    content = await file.read(service.limits.max_upload_bytes + 1)
    if len(content) > service.limits.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "Document exceeds the configured upload limit of "
                f"{service.limits.max_upload_bytes} bytes"
            ),
        )
    try:
        return service.ingest(
            owner_id=current_user.id,
            source_name=file.filename or "upload",
            content=content,
            operator_parser=parser,
        )
    except IntakeValidationError as exc:
        status_code = (
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            if exc.code in {"file_too_large", "too_many_pages"}
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=exc.safe_message)
    except InvalidParserOverrideError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{document_id}", response_model=DocumentResult)
def get_document_extraction(
    document_id: uuid.UUID,
    current_user: CurrentUser,
) -> DocumentResult:
    try:
        return get_service().get(document_id, current_user.id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")


@router.get(
    "/{document_id}/export",
    response_class=Response,
    responses={200: {"content": {"application/json": {}}}},
)
def export_document_extraction(
    document_id: uuid.UUID,
    current_user: CurrentUser,
) -> Response:
    try:
        document = get_service().get(document_id, current_user.id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")
    stem = document.source.source_name.rsplit(".", 1)[0] or "document"
    safe_filename = quote(f"{stem}-extraction.json", safe="")
    return Response(
        content=json.dumps(document_content(document), indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f"attachment; filename*=UTF-8''{safe_filename}"
            ),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_extraction(
    document_id: uuid.UUID,
    current_user: CurrentUser,
) -> Response:
    if not get_service().delete(document_id, current_user.id):
        raise HTTPException(status_code=404, detail="Document not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{document_id}/source",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}},
)
def get_document_source(
    document_id: uuid.UUID,
    current_user: CurrentUser,
) -> Response:
    try:
        content, media_type, filename = get_service().get_source(
            document_id, current_user.id
        )
    except (DocumentNotFoundError, SourceNotFoundError):
        raise HTTPException(status_code=404, detail="Document not found")
    safe_filename = quote(filename, safe="")
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{safe_filename}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/{document_id}/pages/{page_number}/preview",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
)
def get_document_page_preview(
    document_id: uuid.UUID,
    page_number: int,
    current_user: CurrentUser,
) -> Response:
    service = get_service()
    try:
        document = service.get(document_id, current_user.id)
        if not any(page.page_number == page_number for page in document.pages):
            raise InvalidPageError("Page not found")
        content, media_type, filename = service.get_source(
            document_id, current_user.id
        )
        cache = (
            SqlPreviewArtifactCache(service.store.engine, document_id)
            if isinstance(service.store, SqlDocumentStore)
            else None
        )
        artifact = render_preview(
            content,
            media_type,
            page_number,
            source_name=filename,
            source_sha256=document.source.source_sha256,
            config=PreviewConfig(
                dpi=settings.DOCUMENT_EXTRACTOR_PREVIEW_DPI,
                office_binary=settings.DOCUMENT_EXTRACTOR_OFFICE_BINARY,
                office_timeout_seconds=(
                    settings.DOCUMENT_EXTRACTOR_OFFICE_TIMEOUT_SECONDS
                ),
                max_output_pixels=(
                    settings.DOCUMENT_EXTRACTOR_MAX_RENDERED_PIXELS
                ),
                max_concurrent_office=(
                    settings.DOCUMENT_EXTRACTOR_MAX_PARSER_PROCESSES
                ),
                office_memory_bytes=(
                    settings.DOCUMENT_EXTRACTOR_PARSER_MEMORY_MB * 1024 * 1024
                ),
                office_cpu_seconds=(
                    settings.DOCUMENT_EXTRACTOR_PARSER_CPU_SECONDS
                ),
            ),
            cache=cache,
        )
    except (DocumentNotFoundError, SourceNotFoundError, InvalidPageError):
        raise HTTPException(status_code=404, detail="Document or page not found")
    except PreviewError as exc:
        status_by_code = {
            PreviewErrorCode.INVALID_PAGE: 404,
            PreviewErrorCode.UNAVAILABLE: 503,
            PreviewErrorCode.CONVERSION_TIMEOUT: 504,
            PreviewErrorCode.CONVERSION_FAILED: 422,
            PreviewErrorCode.RENDER_FAILED: 422,
        }
        raise HTTPException(
            status_code=status_by_code[exc.code],
            detail=exc.safe_message,
        )
    return Response(
        content=artifact.content,
        media_type=artifact.media_type,
        headers={
            "ETag": f'"{artifact.content_sha256}"',
            "Cache-Control": "private, max-age=300",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.patch(
    "/{document_id}/pages/{page_number}/review",
    response_model=PageResult,
)
def review_document_page(
    document_id: uuid.UUID,
    page_number: int,
    request: PageReviewRequest,
    current_user: CurrentUser,
) -> PageResult:
    try:
        return get_service().review_page(
            document_id, page_number, current_user.id, request
        )
    except (DocumentNotFoundError, InvalidPageError):
        raise HTTPException(status_code=404, detail="Document or page not found")
    except (InvalidReviewTransitionError, ConcurrentDocumentUpdateError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post(
    "/{document_id}/pages/{page_number}/reprocess",
    response_model=PageResult,
)
def reprocess_document_page(
    document_id: uuid.UUID,
    page_number: int,
    request: ReprocessRequest,
    current_user: CurrentUser,
) -> PageResult:
    try:
        return get_service().reprocess_page(
            document_id, page_number, current_user.id, request
        )
    except (DocumentNotFoundError, InvalidPageError):
        raise HTTPException(status_code=404, detail="Document or page not found")
    except InvalidParserOverrideError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ConcurrentDocumentUpdateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
