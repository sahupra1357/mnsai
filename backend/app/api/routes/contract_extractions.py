"""Operator-facing contract field extraction.

Additive: this router reads what the existing document-extraction pipeline
produces and writes only its own table. It has no shell, no fetching, and no write
path outside `contract_field_extraction`.

Every endpoint is owner-scoped through `CurrentUser`. Another owner's extraction is
a 404, not a 403 — its existence is not disclosed.
"""

import uuid
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from pydantic import ValidationError

from app.api.deps import CurrentUser, SessionDep
from app.contract_fields import store
from app.contract_fields.models import (
    ContractFieldResult,
    ContractFieldsPage,
    ExtractionStatus,
    FieldCatalogueResponse,
    FieldSelection,
    VerificationAction,
    VerificationRequest,
)
from app.contract_fields.service import ContractFieldService, to_result, to_row
from app.contract_fields.verification import (
    approval_blockers,
    next_status,
)
from app.visual_document_extractor.intake import IntakeValidationError
from app.visual_document_extractor.service import extraction_service
from app.visual_document_extractor.store import (
    DocumentNotFoundError,
    SourceNotFoundError,
)

router = APIRouter(
    prefix="/contract-extractions",
    tags=["contract-extractions"],
)


def get_service() -> ContractFieldService:
    return ContractFieldService(extraction_service)


def _selection(selected_fields: list[str]) -> FieldSelection:
    """Validate the operator's choice: any non-empty subset of the ten keys.

    An empty selection, an unknown key, or a duplicate is a 422 — the same rule the
    schema states. No key is privileged: a selection of one field is valid, and so is
    one that omits every default-selected field.
    """

    flattened = [
        key.strip()
        for entry in selected_fields
        for key in entry.split(",")
        if key.strip()
    ]
    try:
        return FieldSelection(selected_fields=flattened)
    except ValidationError as exc:
        # Only the message text: a pydantic `ctx` carries the raw exception object,
        # which is not JSON-serializable.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[
                {
                    "loc": ["body", "selected_fields"],
                    "msg": error["msg"],
                    "type": error["type"],
                }
                for error in exc.errors(include_url=False, include_input=False)
            ],
        )


@router.get("/fields", response_model=FieldCatalogueResponse)
def get_field_catalogue(_: CurrentUser) -> FieldCatalogueResponse:
    """The ten-field schema, plus which five the picker starts with selected.

    Served from the backend catalogue so the frontend never keeps a second copy.
    """

    return FieldCatalogueResponse()


@router.get("/records", response_model=ContractFieldsPage)
def list_records(
    session: SessionDep,
    current_user: CurrentUser,
    extraction_status: ExtractionStatus | None = None,
    skip: int = 0,
    limit: int = 50,
) -> ContractFieldsPage:
    """One owner-scoped page of the table, filterable by status."""

    records, count = store.list_extractions(
        session,
        current_user.id,
        extraction_status=extraction_status,
        skip=max(skip, 0),
        limit=max(1, min(limit, 200)),
    )
    return ContractFieldsPage(data=[to_row(record) for record in records], count=count)


@router.post("", response_model=ContractFieldResult)
async def create_contract_extraction(
    session: SessionDep,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    selected_fields: list[str] = Form(default=[]),
) -> ContractFieldResult:
    """Upload a contract, get the ten-key JSON, and persist exactly one row.

    A result whose requested fields did not all resolve comes back **200** with
    `extraction_status="needs_verification"`: it is a business outcome, not a
    transport error, and the row is what the human works from.
    """

    selection = _selection(selected_fields)
    service = get_service()
    content = await file.read()
    try:
        return service.extract(
            session,
            owner_id=current_user.id,
            source_name=file.filename or "contract",
            content=content,
            selected_fields=selection.selected_fields,
        )
    except IntakeValidationError as exc:
        code = (
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            if exc.code in {"file_too_large", "too_many_pages"}
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=exc.safe_message)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )


@router.get("/{extraction_id}", response_model=ContractFieldResult)
def get_contract_extraction(
    extraction_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> ContractFieldResult:
    record = store.get_extraction(session, extraction_id, current_user.id)
    if record is None:
        raise HTTPException(status_code=404, detail="Extraction not found")
    return to_result(record)


@router.patch("/{extraction_id}/verify", response_model=ContractFieldResult)
def verify_contract_extraction(
    extraction_id: uuid.UUID,
    payload: VerificationRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> ContractFieldResult:
    """Save, approve, or reject a human verification.

    `values` accepts requested keys only. `approve` is refused while any unresolved
    field would still be blank — a human cannot approve an incomplete result. The
    ten machine columns are never overwritten; corrections live in `verified_values`.
    """

    record = store.get_extraction(session, extraction_id, current_user.id)
    if record is None:
        raise HTTPException(status_code=404, detail="Extraction not found")

    action = VerificationAction(payload.action)
    if action is VerificationAction.APPROVE:
        blockers = approval_blockers(record, payload.values)
        if blockers:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "These fields are still blank and must be filled in before the "
                    "extraction can be approved: " + ", ".join(blockers)
                ),
            )

    try:
        updated = store.save_verification(
            session,
            extraction_id,
            current_user.id,
            action=action,
            status=next_status(action),
            values=payload.values,
            actor_id=current_user.id,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    if updated is None:
        raise HTTPException(status_code=404, detail="Extraction not found")
    return to_result(updated)


@router.get(
    "/{extraction_id}/source",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}},
)
def get_contract_extraction_source(
    extraction_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Response:
    """The stored source document for the left-hand pane."""

    record = store.get_extraction(session, extraction_id, current_user.id)
    if record is None:
        raise HTTPException(status_code=404, detail="Extraction not found")
    try:
        content, media_type, filename = get_service().get_source(
            record.document_id, current_user.id
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
