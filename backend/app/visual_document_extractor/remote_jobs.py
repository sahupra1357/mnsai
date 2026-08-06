from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, SecretStr
from sqlalchemy import update
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.config import settings
from app.models import DocumentExtractionJobRecord, DocumentJobTokenRecord

from .classification import classify_document
from .intake import IntakeLimits, validate_upload
from .modal_execution import (
    BearerCredential,
    ModalDispatcher,
    ModalDispatchError,
    ModalJobPayload,
    ResultCallback,
    SourceReference,
    generate_opaque_token,
    hash_opaque_token,
    verify_opaque_token,
)
from .models import (
    AdapterResult,
    AttemptStatus,
    AuditEvent,
    DocumentResult,
    DocumentStatus,
    ExtractionAttempt,
    ExtractionSnapshot,
    PageInput,
    PageResult,
    PageStatus,
    ParserSelection,
    utc_now,
)
from .quality import validate_result
from .routing import ExtractionRouter, RoutingOutcome
from .service import DocumentExtractionService
from .store import SqlDocumentStore


class RemoteJobError(RuntimeError):
    def __init__(self, code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


class RemoteResultCallback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: uuid.UUID
    document_id: uuid.UUID
    attempt_id: uuid.UUID
    status: Literal["succeeded", "failed"]
    result: AdapterResult | None = None
    error: dict[str, str | bool] | None = None


_PRIMARY_BY_CLASSIFICATION = {
    "digital": "docling",
    "scanned": "paddleocr",
    "formula_heavy": "mineru",
    "complex_layout": "paddleocr-vl",
    "unknown": "docling",
}

_MODAL_CHAINS = {
    "digital": ("docling", "paddleocr"),
    "scanned": ("paddleocr", "paddleocr-vl"),
    "formula_heavy": ("mineru", "marker"),
    "complex_layout": ("paddleocr-vl", "mineru", "marker"),
    "unknown": ("docling", "paddleocr"),
}


class RemoteJobRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create_job(
        self,
        document: DocumentResult,
        *,
        page_number: int,
        parser: str,
    ) -> DocumentExtractionJobRecord:
        job = DocumentExtractionJobRecord(
            document_id=document.document_id,
            owner_id=document.owner_id,
            page_number=page_number,
            operator_parser=parser,
        )
        with Session(self.engine) as session:
            session.add(job)
            session.commit()
            session.refresh(job)
        return job

    def issue_token(
        self,
        job: DocumentExtractionJobRecord,
        *,
        purpose: Literal["source_download", "result_callback"],
        minutes: int,
        max_uses: int,
    ) -> tuple[DocumentJobTokenRecord, str]:
        generated = generate_opaque_token()
        record = DocumentJobTokenRecord(
            token_id=generated.token_id,
            token_hash=generated.token_hash,
            job_id=job.id,
            document_id=job.document_id,
            purpose=purpose,
            expires_at=(
                datetime.now(timezone.utc) + timedelta(minutes=minutes)
            ).replace(tzinfo=None),
            max_uses=max_uses,
        )
        with Session(self.engine) as session:
            session.add(record)
            session.commit()
            session.refresh(record)
        return record, generated.token

    def authorize(
        self,
        *,
        job_id: uuid.UUID,
        candidate: str,
        purpose: Literal["source_download", "result_callback"],
    ) -> DocumentExtractionJobRecord:
        digest = hash_opaque_token(candidate)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with Session(self.engine) as session:
            token = session.exec(
                select(DocumentJobTokenRecord).where(
                    DocumentJobTokenRecord.job_id == job_id,
                    DocumentJobTokenRecord.token_hash == digest,
                )
            ).first()
            if token is None or not verify_opaque_token(candidate, token.token_hash):
                raise RemoteJobError("token_invalid", "Remote job token is invalid")
            if token.purpose != purpose:
                token.last_failure_code = "token_wrong_purpose"
                session.add(token)
                session.commit()
                raise RemoteJobError(
                    "token_wrong_purpose", "Remote job token is invalid"
                )
            if token.revoked_at is not None or token.expires_at <= now:
                token.last_failure_code = "token_expired_or_revoked"
                session.add(token)
                session.commit()
                raise RemoteJobError(
                    "token_expired_or_revoked", "Remote job token is no longer valid"
                )
            columns = DocumentJobTokenRecord.__table__.c  # type: ignore[attr-defined]
            result = cast(
                Any,
                session.execute(
                    update(DocumentJobTokenRecord)
                    .where(
                        columns.id == token.id,
                        columns.use_count < columns.max_uses,
                        columns.revoked_at.is_(None),
                        columns.expires_at > now,
                    )
                    .values(use_count=columns.use_count + 1, last_used_at=now)
                ),
            )
            if result.rowcount != 1:
                session.rollback()
                raise RemoteJobError(
                    "token_usage_exceeded", "Remote job token is no longer valid"
                )
            job = session.get(DocumentExtractionJobRecord, job_id)
            if job is None or job.document_id != token.document_id:
                session.rollback()
                raise RemoteJobError(
                    "job_not_found", "Remote extraction job was not found"
                )
            session.commit()
            session.refresh(job)
            return job

    def set_dispatched(self, job_id: uuid.UUID, call_id: str) -> None:
        with Session(self.engine) as session:
            job = session.get(DocumentExtractionJobRecord, job_id)
            if job is None:
                raise RemoteJobError(
                    "job_not_found", "Remote extraction job was not found"
                )
            job.status = "running"
            job.remote_call_id = call_id
            job.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            session.add(job)
            session.commit()

    def get_job(self, job_id: uuid.UUID) -> DocumentExtractionJobRecord:
        with Session(self.engine) as session:
            job = session.get(DocumentExtractionJobRecord, job_id)
            if job is None:
                raise RemoteJobError(
                    "job_not_found", "Remote extraction job was not found"
                )
            session.expunge(job)
            return job

    def fail_dispatch(self, job_id: uuid.UUID) -> None:
        """Terminalize a job that Modal never accepted and revoke its credentials."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with Session(self.engine) as session:
            job = session.get(DocumentExtractionJobRecord, job_id)
            if job is None:
                return
            job.status = "dispatch_failed"
            job.updated_at = now
            job.completed_at = now
            session.add(job)
            tokens = session.exec(
                select(DocumentJobTokenRecord).where(
                    DocumentJobTokenRecord.job_id == job_id
                )
            ).all()
            for token in tokens:
                token.revoked_at = now
                token.last_failure_code = "dispatch_failed"
                session.add(token)
            session.commit()

    def complete(
        self, job: DocumentExtractionJobRecord, *, failed: bool = False
    ) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with Session(self.engine) as session:
            current = session.get(DocumentExtractionJobRecord, job.id)
            if current is None:
                return
            current.status = "failed" if failed else "completed"
            current.updated_at = now
            current.completed_at = now
            session.add(current)
            tokens = session.exec(
                select(DocumentJobTokenRecord).where(
                    DocumentJobTokenRecord.job_id == job.id
                )
            ).all()
            for token in tokens:
                if token.purpose == "source_download":
                    token.revoked_at = now
                    session.add(token)
            session.commit()


class ModalExtractionCoordinator:
    def __init__(
        self,
        service: DocumentExtractionService,
        repository: RemoteJobRepository,
        dispatcher: ModalDispatcher,
        *,
        public_base_url: str,
    ) -> None:
        self.service = service
        self.repository = repository
        self.dispatcher = dispatcher
        self.public_base_url = public_base_url.rstrip("/")

    def submit(
        self,
        *,
        owner_id: uuid.UUID,
        source_name: str,
        content: bytes,
        operator_parser: str | None,
    ) -> DocumentResult:
        self.service._validate_parser(operator_parser)
        validated = validate_upload(
            source_name,
            content,
            limits=IntakeLimits(
                max_upload_bytes=self.service.limits.max_upload_bytes,
                max_pages=self.service.limits.max_pages,
                max_image_pixels=self.service.limits.max_image_pixels,
            ),
        )
        self.service._stabilize_office_page_count(validated)
        fingerprint = self.service._extraction_fingerprint(operator_parser)
        cached = self.service.store.find_cached(
            owner_id, validated.metadata.source_sha256, fingerprint
        )
        if cached is not None:
            return cached.model_copy(update={"reused_extraction": True}, deep=True)
        classification = classify_document(self.service._build_page_evidence(validated))
        pages = [
            PageResult(
                page_number=decision.page_number,
                page_status=PageStatus.PENDING,
                classification=decision.classification,
                classification_signals=decision.signals,
                routing_reasons=[*decision.routing_reasons, "execution_backend=modal"],
                warnings=list(validated.warnings),
            )
            for decision in classification.page_decisions
        ]
        document = DocumentResult(
            owner_id=owner_id,
            source=validated.metadata,
            extraction_fingerprint=fingerprint,
            status=DocumentStatus.QUEUED,
            pages=pages,
        )
        self.service.store.create(document, validated.content)
        dispatched_pages = 0
        try:
            for page in pages:
                parser = (
                    operator_parser
                    or _PRIMARY_BY_CLASSIFICATION[page.classification.value]
                )
                self._dispatch_page(document, page, parser)
                dispatched_pages += 1
        except (ModalDispatchError, RemoteJobError, ValueError):
            if dispatched_pages:
                partial = self.service.store.get(document.document_id, owner_id)
                for pending_page in partial.pages[dispatched_pages:]:
                    pending_page.page_status = PageStatus.MANUAL_REVIEW_REQUIRED
                    pending_page.warnings.append(
                        "Modal did not accept this page; reprocess it from the review workspace"
                    )
                partial.status = DocumentStatus.EXTRACTING
                partial.updated_at = utc_now()
                return self.service.store.save(partial, owner_id)
            self.service.store.delete(document.document_id, owner_id)
            return self.service.ingest(
                owner_id=owner_id,
                source_name=source_name,
                content=content,
                operator_parser=operator_parser,
            )
        return document

    def _dispatch_page(
        self, document: DocumentResult, page: PageResult, parser: str
    ) -> None:
        job = self.repository.create_job(
            document, page_number=page.page_number, parser=parser
        )
        callback_record, callback_token = self.repository.issue_token(
            job,
            purpose="result_callback",
            minutes=settings.DOCUMENT_EXTRACTOR_MODAL_RESULT_TOKEN_MINUTES,
            max_uses=3,
        )
        source_url: str | None = None
        source_authorization: BearerCredential | None = None
        if isinstance(self.service.store, SqlDocumentStore):
            source_url = self.service.store.presign_source(
                document.document_id,
                document.owner_id,
                expires_in=settings.DOCUMENT_EXTRACTOR_R2_PRESIGN_SECONDS,
            )
        if source_url is None:
            source_record, source_token = self.repository.issue_token(
                job,
                purpose="source_download",
                minutes=settings.DOCUMENT_EXTRACTOR_MODAL_SOURCE_TOKEN_MINUTES,
                max_uses=settings.DOCUMENT_EXTRACTOR_MODAL_SOURCE_MAX_USES,
            )
            source_url = f"{self.public_base_url}/api/v1/document-extractions/internal/modal/jobs/{job.id}/source"
            source_authorization = BearerCredential(
                token_id=source_record.token_id, token=SecretStr(source_token)
            )
        payload = ModalJobPayload(
            job_id=str(job.id),
            document_id=str(document.document_id),
            attempt_id=str(job.attempt_id),
            parser=parser,  # type: ignore[arg-type]
            source=SourceReference(
                url=source_url,
                authorization=source_authorization,
                sha256=document.source.source_sha256,
                media_type=document.source.media_type,
                source_name=document.source.source_name,
                page_number=page.page_number,
            ),
            result_callback=ResultCallback(
                url=f"{self.public_base_url}/api/v1/document-extractions/internal/modal/jobs/{job.id}/result",
                authorization=BearerCredential(
                    token_id=callback_record.token_id,
                    token=SecretStr(callback_token),
                ),
            ),
            timeout_seconds=min(
                3600, settings.DOCUMENT_EXTRACTOR_MODAL_PARSER_TIMEOUT_SECONDS
            ),
        )
        try:
            receipt = self.dispatcher.dispatch(payload)
        except Exception:
            self.repository.fail_dispatch(job.id)
            raise
        self.repository.set_dispatched(job.id, receipt.call_id)

    def reprocess_page(
        self,
        document_id: uuid.UUID,
        page_number: int,
        owner_id: uuid.UUID,
        parser: str | None,
    ) -> PageResult:
        document = self.service.store.get(document_id, owner_id)
        page = self.service._page(document, page_number)
        if parser is not None and parser not in {
            "docling",
            "paddleocr",
            "paddleocr-vl",
            "mineru",
            "marker",
        }:
            raise RemoteJobError(
                "modal_parser_unavailable",
                "The requested parser is not available in Modal",
            )
        selected = parser or _PRIMARY_BY_CLASSIFICATION[page.classification.value]
        if page.elements:
            page.extraction_history.append(
                ExtractionSnapshot(
                    parser_run_id=(
                        page.selected_parser.run_id if page.selected_parser else None
                    ),
                    reason="pre_modal_reprocess_review_state",
                    elements=page.elements,
                    warnings=page.warnings,
                )
            )
        page.page_status = PageStatus.EXTRACTING
        page.audit_events.append(
            AuditEvent(
                event_type="modal_reprocess_requested",
                actor_id=owner_id,
                details={"parser": selected},
            )
        )
        document.status = DocumentStatus.EXTRACTING
        document.updated_at = utc_now()
        saved = self.service.store.save(document, owner_id)
        saved_page = self.service._page(saved, page_number)
        self._dispatch_page(saved, saved_page, selected)
        return saved_page.model_copy(deep=True)

    def accept_result(
        self, job: DocumentExtractionJobRecord, callback: RemoteResultCallback
    ) -> DocumentResult:
        if (
            callback.attempt_id != job.attempt_id
            or callback.document_id != job.document_id
        ):
            raise RemoteJobError(
                "callback_mismatch", "Remote callback does not match its job"
            )
        document = self.service.store.get(job.document_id, job.owner_id)
        page = self.service._page(document, job.page_number)
        if job.status == "completed":
            return document
        failed = callback.status == "failed" or callback.result is None
        assessment = None
        selected_via = "modal"
        if not failed:
            result = callback.result
            assert result is not None
            source, media_type, _ = self.service.store.get_source(
                document.document_id, document.owner_id
            )
            page_input = PageInput(
                document_id=document.document_id,
                page_number=page.page_number,
                media_type=media_type,
                content=source,
                classification=page.classification,
                signals=page.classification_signals,
            )
            assessment = validate_result(
                page_input,
                result,
                self.service.router.quality_policy,
            )
            page.attempts.append(
                result.attempt.model_copy(
                    update={"quality_signals": list(assessment.signals)}
                )
            )
            if not assessment.passed:
                next_parser = self._next_modal_parser(page, job, result)
                if next_parser is not None:
                    page.page_status = PageStatus.EXTRACTING
                    page.routing_reasons.append(
                        f"modal_fallback={next_parser} after {job.operator_parser}"
                    )
                    document.status = DocumentStatus.FALLBACK
                    document.updated_at = utc_now()
                    saved = self.service.store.save(document, document.owner_id)
                    self.repository.complete(job, failed=True)
                    try:
                        self._dispatch_page(saved, page, next_parser)
                    except (ModalDispatchError, RemoteJobError, ValueError):
                        saved_page = self.service._page(saved, page.page_number)
                        saved_page.page_status = PageStatus.MANUAL_REVIEW_REQUIRED
                        saved_page.warnings.append(
                            "Modal fallback dispatch failed; manual review is required"
                        )
                        saved.status = DocumentStatus.NEEDS_REVIEW
                        saved = self.service.store.save(saved, saved.owner_id)
                    return saved
                provider_outcome = self._provider_fallback(page_input)
                page.attempts.extend(provider_outcome.attempts)
                page.routing_reasons.extend(provider_outcome.routing_reasons)
                if provider_outcome.selected_result is not None:
                    result = provider_outcome.selected_result
                    assessment = provider_outcome.assessment
                    selected_via = "remote_provider_fallback"
            page.elements = result.elements
            page.warnings.extend(result.warnings)
            page.confidence = result.attempt.confidence
            page.confidence_source = (
                f"{result.attempt.parser}:page_mean"
                if result.attempt.confidence is not None
                else None
            )
            page.selected_parser = ParserSelection(
                name=result.attempt.parser,
                version=result.attempt.version,
                run_id=result.attempt.run_id,
                rationale=(
                    f"Selected via {selected_via}"
                    if assessment is not None and assessment.passed
                    else f"Best available {selected_via} result requires manual review"
                ),
            )
            page.page_status = (
                PageStatus.NEEDS_REVIEW
                if assessment is not None and assessment.passed
                else PageStatus.MANUAL_REVIEW_REQUIRED
            )
            page.extraction_history.append(
                ExtractionSnapshot(
                    parser_run_id=result.attempt.run_id,
                    reason="modal_selected_result",
                    elements=result.elements,
                    warnings=result.warnings,
                )
            )
        else:
            error = callback.error or {}
            failed_result = AdapterResult(
                attempt=ExtractionAttempt(
                    parser=job.operator_parser or "modal-parser",
                    version="modal",
                    status=AttemptStatus.FAILED,
                    error_code=str(error.get("code") or "modal_parser_failed"),
                    error_message=str(
                        error.get("message") or "Modal parser execution failed"
                    ),
                    retryable=bool(error.get("retryable", False)),
                )
            )
            page.attempts.append(failed_result.attempt)
            next_parser = self._next_modal_parser(page, job, failed_result)
            if next_parser is not None:
                page.page_status = PageStatus.EXTRACTING
                page.routing_reasons.append(
                    f"modal_fallback={next_parser} after {job.operator_parser}"
                )
                document.status = DocumentStatus.FALLBACK
                document.updated_at = utc_now()
                saved = self.service.store.save(document, document.owner_id)
                self.repository.complete(job, failed=True)
                try:
                    self._dispatch_page(saved, page, next_parser)
                except (ModalDispatchError, RemoteJobError, ValueError):
                    saved_page = self.service._page(saved, page.page_number)
                    saved_page.page_status = PageStatus.MANUAL_REVIEW_REQUIRED
                    saved_page.warnings.append(
                        "Modal fallback dispatch failed; manual review is required"
                    )
                    saved.status = DocumentStatus.NEEDS_REVIEW
                    saved = self.service.store.save(saved, saved.owner_id)
                return saved
            source, media_type, _ = self.service.store.get_source(
                document.document_id, document.owner_id
            )
            provider_outcome = self._provider_fallback(
                PageInput(
                    document_id=document.document_id,
                    page_number=page.page_number,
                    media_type=media_type,
                    content=source,
                    classification=page.classification,
                    signals=page.classification_signals,
                )
            )
            page.attempts.extend(provider_outcome.attempts)
            page.routing_reasons.extend(provider_outcome.routing_reasons)
            provider_result = provider_outcome.selected_result
            if provider_result is None:
                page.page_status = PageStatus.MANUAL_REVIEW_REQUIRED
                page.warnings.append("Modal parser failed; manual review is required")
            else:
                provider_assessment = provider_outcome.assessment
                page.elements = provider_result.elements
                page.warnings.extend(provider_result.warnings)
                page.confidence = provider_result.attempt.confidence
                page.confidence_source = (
                    f"{provider_result.attempt.parser}:page_mean"
                    if provider_result.attempt.confidence is not None
                    else None
                )
                page.selected_parser = ParserSelection(
                    name=provider_result.attempt.parser,
                    version=provider_result.attempt.version,
                    run_id=provider_result.attempt.run_id,
                    rationale="Selected via remote provider fallback",
                )
                page.page_status = (
                    PageStatus.NEEDS_REVIEW
                    if provider_assessment is not None and provider_assessment.passed
                    else PageStatus.MANUAL_REVIEW_REQUIRED
                )
                failed = False
        page.audit_events.append(
            AuditEvent(
                event_type="modal_extraction_completed",
                details={"job_id": str(job.id), "failed": failed},
            )
        )
        document.status = (
            DocumentStatus.NEEDS_REVIEW
            if all(
                item.page_status not in {PageStatus.PENDING, PageStatus.EXTRACTING}
                for item in document.pages
            )
            else DocumentStatus.EXTRACTING
        )
        document.updated_at = utc_now()
        saved = self.service.store.save(document, document.owner_id)
        self.repository.complete(job, failed=failed)
        return saved

    def _next_modal_parser(
        self,
        page: PageResult,
        job: DocumentExtractionJobRecord,
        result: AdapterResult,
    ) -> str | None:
        current = job.operator_parser or result.attempt.parser
        same_parser_attempts = sum(
            attempt.parser == current for attempt in page.attempts
        )
        if (
            result.attempt.retryable
            and same_parser_attempts <= settings.DOCUMENT_EXTRACTOR_TRANSIENT_RETRIES
        ):
            return current
        chain = _MODAL_CHAINS[page.classification.value]
        if current not in chain:
            return chain[0]
        index = chain.index(current) + 1
        return chain[index] if index < len(chain) else None

    def _provider_fallback(self, page_input: PageInput) -> RoutingOutcome:
        provider_names = {
            "mistral-ocr",
            "openai-vision-terra",
            "openai-vision-sol",
        }
        adapters = [
            adapter
            for adapter in self.service.router._adapters
            if adapter.name in provider_names
        ]
        router = ExtractionRouter(
            adapters,
            policy=self.service.router.policy,
            quality_policy=self.service.router.quality_policy,
        )
        return router.extract(
            page_input.model_copy(update={"operator_parser": "mistral-ocr"})
        )
