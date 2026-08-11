import json
import uuid
from urllib.parse import quote

from fastapi import (
    APIRouter,
    File,
    Form,
    Header,
    HTTPException,
    Response,
    UploadFile,
    status,
)

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.db import engine
from app.visual_document_extractor.api_keys import (
    ApiKeyCreated,
    ApiKeyCreateRequest,
    ApiKeyMetadata,
    ApiKeyRepository,
)
from app.visual_document_extractor.export import document_content
from app.visual_document_extractor.intake import IntakeValidationError
from app.visual_document_extractor.modal_execution import ModalDispatcher
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
from app.visual_document_extractor.remote_jobs import (
    ModalExtractionCoordinator,
    RemoteJobError,
    RemoteJobRepository,
    RemoteResultCallback,
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


def get_modal_coordinator() -> ModalExtractionCoordinator | None:
    service = get_service()
    if (
        not isinstance(service.store, SqlDocumentStore)
        or not settings.DOCUMENT_EXTRACTOR_MODAL_ENDPOINT_URL
        or not settings.DOCUMENT_EXTRACTOR_MODAL_KEY
        or not settings.DOCUMENT_EXTRACTOR_MODAL_SECRET
        or not settings.DOCUMENT_EXTRACTOR_PUBLIC_BASE_URL
    ):
        return None
    return ModalExtractionCoordinator(
        service,
        RemoteJobRepository(service.store.engine),
        ModalDispatcher(
            endpoint_url=settings.DOCUMENT_EXTRACTOR_MODAL_ENDPOINT_URL,
            endpoint_key=settings.DOCUMENT_EXTRACTOR_MODAL_KEY,
            endpoint_secret=settings.DOCUMENT_EXTRACTOR_MODAL_SECRET,
            timeout_seconds=(
                settings.DOCUMENT_EXTRACTOR_MODAL_DISPATCH_TIMEOUT_SECONDS
            ),
        ),
        public_base_url=settings.DOCUMENT_EXTRACTOR_PUBLIC_BASE_URL,
    )


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
    return await _ingest_upload(current_user.id, file, parser)


async def _ingest_upload(
    owner_id: uuid.UUID,
    file: UploadFile,
    parser: str | None,
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
        coordinator = get_modal_coordinator()
        if settings.DOCUMENT_EXTRACTOR_MODAL_ENABLED and coordinator is not None:
            return coordinator.submit(
                owner_id=owner_id,
                source_name=file.filename or "upload",
                content=content,
                operator_parser=parser,
            )
        return service.ingest(
            owner_id=owner_id,
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


@router.post(
    "/api-keys", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED
)
def create_document_extraction_api_key(
    request: ApiKeyCreateRequest,
    current_user: CurrentUser,
) -> ApiKeyCreated:
    """Create an API key; the plaintext value is returned exactly once."""
    return ApiKeyRepository(engine).create(current_user.id, request.name)


@router.get("/api-keys", response_model=list[ApiKeyMetadata])
def list_document_extraction_api_keys(
    current_user: CurrentUser,
) -> list[ApiKeyMetadata]:
    return ApiKeyRepository(engine).list(current_user.id)


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_document_extraction_api_key(
    key_id: uuid.UUID,
    current_user: CurrentUser,
) -> Response:
    if not ApiKeyRepository(engine).revoke(current_user.id, key_id):
        raise HTTPException(status_code=404, detail="API key not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api-keys/{key_id}/rotate", response_model=ApiKeyCreated)
def rotate_document_extraction_api_key(
    key_id: uuid.UUID,
    current_user: CurrentUser,
) -> ApiKeyCreated:
    replacement = ApiKeyRepository(engine).rotate(current_user.id, key_id)
    if replacement is None:
        raise HTTPException(status_code=404, detail="Active API key not found")
    return replacement


@router.post(
    "/programmatic", response_model=DocumentResult, status_code=status.HTTP_201_CREATED
)
async def create_programmatic_document_extraction(
    file: UploadFile = File(...),
    parser: str | None = Form(default=None),
    x_api_key: str | None = Header(default=None),
) -> DocumentResult:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="A valid X-API-Key is required")
    owner_id = ApiKeyRepository(engine).authenticate(x_api_key)
    if owner_id is None:
        raise HTTPException(status_code=401, detail="A valid X-API-Key is required")
    return await _ingest_upload(owner_id, file, parser)


@router.get("/programmatic/{document_id}", response_model=DocumentResult)
def get_programmatic_document_extraction(
    document_id: uuid.UUID,
    x_api_key: str | None = Header(default=None),
) -> DocumentResult:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="A valid X-API-Key is required")
    owner_id = ApiKeyRepository(engine).authenticate(x_api_key)
    if owner_id is None:
        raise HTTPException(status_code=401, detail="A valid X-API-Key is required")
    try:
        return get_service().get(document_id, owner_id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Remote job authorization failed")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Remote job authorization failed")
    return token


@router.get(
    "/internal/modal/jobs/{job_id}/source",
    response_class=Response,
    include_in_schema=False,
)
def get_modal_job_source(
    job_id: uuid.UUID,
    authorization: str | None = Header(default=None),
) -> Response:
    service = get_service()
    if not isinstance(service.store, SqlDocumentStore):
        raise HTTPException(status_code=404, detail="Remote extraction job not found")
    repository = RemoteJobRepository(service.store.engine)
    try:
        job = repository.authorize(
            job_id=job_id,
            candidate=_bearer_token(authorization),
            purpose="source_download",
        )
        content, media_type, _ = service.get_source(job.document_id, job.owner_id)
    except (RemoteJobError, DocumentNotFoundError, SourceNotFoundError):
        raise HTTPException(status_code=401, detail="Remote job authorization failed")
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post(
    "/internal/modal/jobs/{job_id}/result",
    response_model=DocumentResult,
    include_in_schema=False,
)
def save_modal_job_result(
    job_id: uuid.UUID,
    callback: RemoteResultCallback,
    authorization: str | None = Header(default=None),
) -> DocumentResult:
    coordinator = get_modal_coordinator()
    if coordinator is None:
        raise HTTPException(status_code=404, detail="Remote extraction job not found")
    job = None
    try:
        job = coordinator.repository.authorize(
            job_id=job_id,
            candidate=_bearer_token(authorization),
            purpose="result_callback",
        )
        for conflict_attempt in range(3):
            try:
                return coordinator.accept_result(job, callback)
            except ConcurrentDocumentUpdateError:
                job = coordinator.repository.get_job(job_id)
                if job.status == "completed":
                    return get_service().get(job.document_id, job.owner_id)
                if conflict_attempt == 2:
                    raise HTTPException(
                        status_code=409, detail="Remote callback conflict; retry callback"
                    )
        raise HTTPException(status_code=409, detail="Remote callback conflict")
    except ConcurrentDocumentUpdateError:
        raise HTTPException(status_code=409, detail="Remote callback conflict")
    except RemoteJobError:
        raise HTTPException(status_code=401, detail="Remote job authorization failed")


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
            "Content-Disposition": (f"attachment; filename*=UTF-8''{safe_filename}"),
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
        content, media_type, filename = service.get_source(document_id, current_user.id)
        cache = (
            SqlPreviewArtifactCache(
                service.store.engine,
                document_id,
                object_storage=service.store.object_storage,
                object_prefix=service.store.object_prefix,
                fallback_to_postgres=service.store.fallback_to_postgres,
            )
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
                max_output_pixels=(settings.DOCUMENT_EXTRACTOR_MAX_RENDERED_PIXELS),
                max_concurrent_office=(
                    settings.DOCUMENT_EXTRACTOR_MAX_PARSER_PROCESSES
                ),
                office_memory_bytes=(
                    settings.DOCUMENT_EXTRACTOR_PARSER_MEMORY_MB * 1024 * 1024
                ),
                office_cpu_seconds=(settings.DOCUMENT_EXTRACTOR_PARSER_CPU_SECONDS),
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
        coordinator = get_modal_coordinator()
        if settings.DOCUMENT_EXTRACTOR_MODAL_ENABLED and coordinator is not None:
            try:
                return coordinator.reprocess_page(
                    document_id,
                    page_number,
                    current_user.id,
                    request.parser,
                )
            except (RemoteJobError, ValueError):
                # A dispatch/configuration failure uses the existing bounded local path.
                pass
        return get_service().reprocess_page(
            document_id, page_number, current_user.id, request
        )
    except (DocumentNotFoundError, InvalidPageError):
        raise HTTPException(status_code=404, detail="Document or page not found")
    except InvalidParserOverrideError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ConcurrentDocumentUpdateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
