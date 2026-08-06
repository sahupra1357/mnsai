from __future__ import annotations

import hashlib
import io
import uuid
from pathlib import Path

import pytest
from PIL import Image
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import settings
from app.models import DocumentExtractionJobRecord, DocumentJobTokenRecord
from app.visual_document_extractor.adapters import PaddleOCRAdapter
from app.visual_document_extractor.modal_execution import ModalDispatchReceipt
from app.visual_document_extractor.models import (
    AdapterResult,
    AttemptStatus,
    ExtractedElement,
    ExtractionAttempt,
)
from app.visual_document_extractor.remote_jobs import (
    ModalExtractionCoordinator,
    RemoteJobError,
    RemoteJobRepository,
    RemoteResultCallback,
)
from app.visual_document_extractor.routing import ExtractionRouter
from app.visual_document_extractor.service import DocumentExtractionService
from app.visual_document_extractor.store import SqlDocumentStore

OWNER = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (100, 40), "white").save(output, format="PNG")
    return output.getvalue()


def _result() -> AdapterResult:
    return AdapterResult(
        attempt=ExtractionAttempt(
            parser="paddleocr",
            version="modal-test",
            status=AttemptStatus.SUCCEEDED,
            confidence=0.99,
        ),
        elements=[
            ExtractedElement(
                element_id="p1-1",
                text="Remote extracted text",
                reading_order=0,
                confidence=0.99,
            )
        ],
    )


class CapturingDispatcher:
    def __init__(self) -> None:
        self.payloads = []

    def dispatch(self, payload):
        self.payloads.append(payload)
        return ModalDispatchReceipt(call_id="fc-test")


@pytest.fixture
def coordinator(tmp_path: Path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'remote.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    adapter = PaddleOCRAdapter(executor=lambda _page: _result(), version="test")
    service = DocumentExtractionService(
        store=SqlDocumentStore(engine),
        router=ExtractionRouter([adapter]),
    )
    dispatcher = CapturingDispatcher()
    value = ModalExtractionCoordinator(
        service,
        RemoteJobRepository(engine),
        dispatcher,  # type: ignore[arg-type]
        public_base_url="https://api.example.test",
    )
    return value, dispatcher


def test_remote_submission_queues_and_uses_separate_opaque_tokens(coordinator) -> None:
    value, dispatcher = coordinator
    content = _png()

    document = value.submit(
        owner_id=OWNER,
        source_name="scan.png",
        content=content,
        operator_parser="paddleocr",
    )

    assert document.status.value == "queued"
    assert len(dispatcher.payloads) == 1
    payload = dispatcher.payloads[0]
    assert payload.source.sha256 == hashlib.sha256(content).hexdigest()
    assert (
        payload.timeout_seconds
        == settings.DOCUMENT_EXTRACTOR_MODAL_PARSER_TIMEOUT_SECONDS
    )
    assert payload.source.authorization is not None
    assert (
        payload.source.authorization.token.get_secret_value()
        != payload.result_callback.authorization.token.get_secret_value()
    )


def test_failed_dispatch_terminalizes_job_and_revokes_tokens(coordinator) -> None:
    value, _ = coordinator
    document = value.service.ingest(
        owner_id=OWNER,
        source_name="scan.png",
        content=_png(),
        operator_parser="paddleocr",
    )
    job = value.repository.create_job(document, page_number=1, parser="paddleocr")
    value.repository.issue_token(
        job, purpose="source_download", minutes=5, max_uses=1
    )
    value.repository.issue_token(
        job, purpose="result_callback", minutes=5, max_uses=1
    )
    value.repository.fail_dispatch(job.id)

    with Session(value.repository.engine) as session:
        stored_job = session.exec(select(DocumentExtractionJobRecord)).one()
        tokens = session.exec(select(DocumentJobTokenRecord)).all()
    assert stored_job.status == "dispatch_failed"
    assert stored_job.completed_at is not None
    assert tokens
    assert all(token.revoked_at is not None for token in tokens)


def test_callback_is_idempotent_and_source_token_is_purpose_bound(coordinator) -> None:
    value, dispatcher = coordinator
    document = value.submit(
        owner_id=OWNER,
        source_name="scan.png",
        content=_png(),
        operator_parser="paddleocr",
    )
    payload = dispatcher.payloads[0]
    source = payload.source.authorization
    callback_credential = payload.result_callback.authorization
    assert source is not None

    with pytest.raises(RemoteJobError) as wrong_purpose:
        value.repository.authorize(
            job_id=uuid.UUID(payload.job_id),
            candidate=source.token.get_secret_value(),
            purpose="result_callback",
        )
    assert wrong_purpose.value.code == "token_wrong_purpose"

    job = value.repository.authorize(
        job_id=uuid.UUID(payload.job_id),
        candidate=callback_credential.token.get_secret_value(),
        purpose="result_callback",
    )
    callback = RemoteResultCallback(
        job_id=job.id,
        document_id=document.document_id,
        attempt_id=job.attempt_id,
        status="succeeded",
        result=_result(),
    )
    completed = value.accept_result(job, callback)
    assert completed.status.value == "needs_review"
    assert completed.pages[0].elements[0].text == "Remote extracted text"

    duplicate_job = value.repository.authorize(
        job_id=job.id,
        candidate=callback_credential.token.get_secret_value(),
        purpose="result_callback",
    )
    duplicate = value.accept_result(duplicate_job, callback)
    assert duplicate.revision == completed.revision


def test_low_quality_modal_result_dispatches_distinct_page_fallback(
    coordinator,
) -> None:
    value, dispatcher = coordinator
    document = value.submit(
        owner_id=OWNER,
        source_name="scan.png",
        content=_png(),
        operator_parser=None,
    )
    first = dispatcher.payloads[0]
    credential = first.result_callback.authorization
    job = value.repository.authorize(
        job_id=uuid.UUID(first.job_id),
        candidate=credential.token.get_secret_value(),
        purpose="result_callback",
    )
    low_quality = AdapterResult(
        attempt=ExtractionAttempt(
            parser="paddleocr",
            version="modal-test",
            status=AttemptStatus.LOW_CONFIDENCE,
            confidence=0.1,
        ),
        elements=[],
    )

    queued = value.accept_result(
        job,
        RemoteResultCallback(
            job_id=job.id,
            document_id=document.document_id,
            attempt_id=job.attempt_id,
            status="succeeded",
            result=low_quality,
        ),
    )

    assert queued.status.value == "fallback"
    assert len(dispatcher.payloads) == 2
    assert dispatcher.payloads[1].parser == "paddleocr-vl"
