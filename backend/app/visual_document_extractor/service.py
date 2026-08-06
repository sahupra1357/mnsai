from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass

from app.core.config import settings
from app.core.db import engine
from app.visual_document_extractor.adapters import (
    DoclingAdapter,
    MarkerAdapter,
    MinerUAdapter,
    MistralOCRAdapter,
    OpenAIVisionAdapter,
    PaddleOCRAdapter,
    PaddleOCRVLAdapter,
    SecondaryOCRAdapter,
)
from app.visual_document_extractor.candidates import (
    add_candidate,
    preserve_current_candidate,
    select_best_candidate,
)
from app.visual_document_extractor.classification import (
    PageEvidence,
    classify_document,
)
from app.visual_document_extractor.execution import ProcessLimits
from app.visual_document_extractor.intake import (
    SUPPORTED_EXTENSIONS,
    IntakeErrorCode,
    IntakeLimits,
    IntakeValidationError,
    ValidatedSource,
    validate_upload,
)
from app.visual_document_extractor.models import (
    AdapterCapability,
    AuditEvent,
    CapabilityResponse,
    DocumentResult,
    DocumentStatus,
    ExtractionSnapshot,
    PageInput,
    PageResult,
    PageReviewRequest,
    PageStatus,
    ParserSelection,
    ReprocessRequest,
    ReviewStatus,
    utc_now,
)
from app.visual_document_extractor.preview import (
    PreviewConfig,
    PreviewError,
    convert_office_to_pdf,
)
from app.visual_document_extractor.quality import QualityPolicy
from app.visual_document_extractor.routing import ExtractionRouter, RoutingPolicy
from app.visual_document_extractor.storage_config import configured_storage
from app.visual_document_extractor.store import (
    DocumentStore,
    InMemoryDocumentStore,
    SqlDocumentStore,
)


class InvalidPageError(LookupError):
    pass


class InvalidReviewTransitionError(ValueError):
    pass


class InvalidParserOverrideError(ValueError):
    pass


@dataclass(frozen=True)
class ServiceLimits:
    max_upload_bytes: int
    max_pages: int
    max_image_pixels: int
    parser_timeout_seconds: float


_MODAL_PARSER_VERSIONS = {
    "docling": "2.114.0",
    "paddleocr": "3.7.0",
    "paddleocr-vl": "3.7.0",
    "mineru": "3.4.4",
    "marker": "2.0.0",
}


def default_router() -> ExtractionRouter:
    """Create the configured adapter registry without loading optional engines."""
    process_limits = ProcessLimits(
        max_concurrent=settings.DOCUMENT_EXTRACTOR_MAX_PARSER_PROCESSES,
        memory_bytes=settings.DOCUMENT_EXTRACTOR_PARSER_MEMORY_MB * 1024 * 1024,
        cpu_seconds=settings.DOCUMENT_EXTRACTOR_PARSER_CPU_SECONDS,
    )
    return ExtractionRouter(
        [
            DoclingAdapter(process_limits=process_limits),
            PaddleOCRAdapter(process_limits=process_limits),
            PaddleOCRVLAdapter(process_limits=process_limits),
            MinerUAdapter(process_limits=process_limits),
            MarkerAdapter(process_limits=process_limits),
            SecondaryOCRAdapter(process_limits=process_limits),
            MistralOCRAdapter(
                enabled=settings.DOCUMENT_EXTRACTOR_MISTRAL_ENABLED,
                api_key_configured=bool(settings.MISTRAL_API_KEY),
                model=settings.DOCUMENT_EXTRACTOR_MISTRAL_MODEL,
                process_limits=process_limits,
            ),
            OpenAIVisionAdapter(
                name="openai-vision-terra",
                enabled=settings.DOCUMENT_EXTRACTOR_OPENAI_VISION_ENABLED,
                api_key_configured=bool(settings.OPENAI_API_KEY),
                model=settings.DOCUMENT_EXTRACTOR_OPENAI_DEFAULT_MODEL,
                process_limits=process_limits,
            ),
            OpenAIVisionAdapter(
                name="openai-vision-sol",
                enabled=settings.DOCUMENT_EXTRACTOR_OPENAI_VISION_ENABLED,
                api_key_configured=bool(settings.OPENAI_API_KEY),
                model=settings.DOCUMENT_EXTRACTOR_OPENAI_ESCALATION_MODEL,
                process_limits=process_limits,
            ),
        ],
        policy=RoutingPolicy(
            transient_retries_per_adapter=(
                settings.DOCUMENT_EXTRACTOR_TRANSIENT_RETRIES
            ),
            max_alternate_attempts=(settings.DOCUMENT_EXTRACTOR_ALTERNATE_ATTEMPTS),
            max_vision_attempts=settings.DOCUMENT_EXTRACTOR_VISION_ATTEMPTS,
        ),
        quality_policy=QualityPolicy(
            minimum_confidence=settings.DOCUMENT_EXTRACTOR_MINIMUM_CONFIDENCE
        ),
    )


class DocumentExtractionService:
    def __init__(
        self,
        *,
        store: DocumentStore | None = None,
        router: ExtractionRouter | None = None,
        limits: ServiceLimits | None = None,
    ) -> None:
        if store is not None:
            self.store = store
        elif settings.DOCUMENT_EXTRACTOR_USE_DURABLE_STORE:
            storage = configured_storage()
            self.store = SqlDocumentStore(
                engine,
                object_storage=storage.object_storage,
                object_prefix=settings.DOCUMENT_EXTRACTOR_R2_PREFIX,
                fallback_to_postgres=(
                    settings.DOCUMENT_EXTRACTOR_STORAGE_FALLBACK_TO_POSTGRES
                ),
            )
        else:
            self.store = InMemoryDocumentStore()
        self.router = router or default_router()
        self.limits = limits or ServiceLimits(
            max_upload_bytes=settings.DOCUMENT_EXTRACTOR_MAX_UPLOAD_BYTES,
            max_pages=settings.DOCUMENT_EXTRACTOR_MAX_PAGES,
            max_image_pixels=settings.DOCUMENT_EXTRACTOR_MAX_RENDERED_PIXELS,
            parser_timeout_seconds=(settings.DOCUMENT_EXTRACTOR_PARSER_TIMEOUT_SECONDS),
        )

    def capabilities(self) -> CapabilityResponse:
        modal_configured = self._modal_configured()
        return CapabilityResponse(
            adapters=self._effective_capabilities(modal_configured=modal_configured),
            supported_extensions=list(SUPPORTED_EXTENSIONS),
            max_upload_bytes=self.limits.max_upload_bytes,
            max_pages=self.limits.max_pages,
            retry_limits={
                "transient_retries_per_adapter": (
                    settings.DOCUMENT_EXTRACTOR_TRANSIENT_RETRIES
                ),
                "alternate_attempts": (settings.DOCUMENT_EXTRACTOR_ALTERNATE_ATTEMPTS),
                "vision_attempts": settings.DOCUMENT_EXTRACTOR_VISION_ATTEMPTS,
            },
            storage_provider=(
                self.store.storage_provider
                if isinstance(self.store, SqlDocumentStore)
                else "memory"
            ),
            execution_backend=("modal" if modal_configured else "local"),
            modal_enabled=modal_configured,
        )

    def _effective_capabilities(
        self, *, modal_configured: bool | None = None
    ) -> list[AdapterCapability]:
        if modal_configured is None:
            modal_configured = self._modal_configured()
        capabilities = self.router.capabilities()
        if not modal_configured:
            return capabilities
        return [
            capability.model_copy(
                update={
                    "version": _MODAL_PARSER_VERSIONS[capability.name],
                    "available": True,
                    "reason": "Executed remotely on Modal",
                }
            )
            if capability.name in _MODAL_PARSER_VERSIONS
            else capability
            for capability in capabilities
        ]

    def _modal_configured(self) -> bool:
        return bool(
            settings.DOCUMENT_EXTRACTOR_MODAL_ENABLED
            and isinstance(self.store, SqlDocumentStore)
            and settings.DOCUMENT_EXTRACTOR_MODAL_ENDPOINT_URL
            and settings.DOCUMENT_EXTRACTOR_MODAL_KEY
            and settings.DOCUMENT_EXTRACTOR_MODAL_SECRET
            and settings.DOCUMENT_EXTRACTOR_PUBLIC_BASE_URL
        )

    def ingest(
        self,
        *,
        owner_id: uuid.UUID,
        source_name: str,
        content: bytes,
        operator_parser: str | None = None,
    ) -> DocumentResult:
        self._validate_parser(operator_parser)
        validated = validate_upload(
            source_name,
            content,
            limits=IntakeLimits(
                max_upload_bytes=self.limits.max_upload_bytes,
                max_pages=self.limits.max_pages,
                max_image_pixels=self.limits.max_image_pixels,
            ),
        )
        self._stabilize_office_page_count(validated)
        extraction_fingerprint = self._extraction_fingerprint(operator_parser)
        cached = self.store.find_cached(
            owner_id,
            validated.metadata.source_sha256,
            extraction_fingerprint,
        )
        if cached is not None:
            return cached.model_copy(update={"reused_extraction": True}, deep=True)
        document = DocumentResult(
            owner_id=owner_id,
            source=validated.metadata,
            status=DocumentStatus.CLASSIFYING,
            extraction_fingerprint=extraction_fingerprint,
        )
        self.store.create(document, validated.content)

        evidence = self._build_page_evidence(validated)
        classification = classify_document(evidence)
        document.status = DocumentStatus.EXTRACTING
        document.pages = []

        for decision in classification.page_decisions:
            page_input = PageInput(
                document_id=document.document_id,
                page_number=decision.page_number,
                media_type=validated.metadata.media_type,
                content=validated.content,
                classification=decision.classification,
                signals=decision.signals,
                timeout_seconds=self.limits.parser_timeout_seconds,
                operator_parser=operator_parser,
            )
            outcome = self.router.extract(page_input)
            selected = outcome.selected_result
            page_status = (
                PageStatus.MANUAL_REVIEW_REQUIRED
                if outcome.manual_review_required or selected is None
                else PageStatus.NEEDS_REVIEW
            )
            selected_parser = None
            elements = []
            warnings = list(validated.warnings)
            if selected is not None:
                selected_parser = ParserSelection(
                    name=selected.attempt.parser,
                    version=selected.attempt.version,
                    run_id=selected.attempt.run_id,
                    rationale="; ".join(outcome.routing_reasons)
                    or "best passing candidate",
                )
                elements = selected.elements
                warnings.extend(selected.warnings)

            page_result = PageResult(
                    page_number=decision.page_number,
                    page_status=page_status,
                    confidence=(
                        selected.attempt.confidence if selected is not None else None
                    ),
                    confidence_source=(
                        f"{selected.attempt.parser}:page_mean"
                        if selected is not None
                        and selected.attempt.confidence is not None
                        else None
                    ),
                    classification=decision.classification,
                    classification_signals=decision.signals,
                    routing_reasons=[
                        *decision.routing_reasons,
                        *(
                            [f"operator override requested parser={operator_parser}"]
                            if operator_parser
                            else []
                        ),
                        *outcome.routing_reasons,
                    ],
                    selected_parser=selected_parser,
                    attempts=list(outcome.attempts),
                    elements=elements,
                    extraction_history=(
                        [
                            ExtractionSnapshot(
                                parser_run_id=selected.attempt.run_id,
                                reason="initial_selected_result",
                                elements=selected.elements,
                                warnings=selected.warnings,
                            )
                        ]
                        if selected is not None
                        else []
                    ),
                    warnings=warnings,
                    audit_events=[
                        AuditEvent(
                            event_type="extraction_completed",
                            details={
                                "manual_review_required": (
                                    outcome.manual_review_required
                                )
                            },
                        )
                    ],
                )
            if selected is not None:
                add_candidate(
                    page_result,
                    selected,
                    quality_passed=not outcome.manual_review_required,
                    rationale="; ".join(outcome.routing_reasons)
                    or "best passing candidate",
                )
                select_best_candidate(page_result)
                page_result.warnings = list(
                    dict.fromkeys([*validated.warnings, *page_result.warnings])
                )
            document.pages.append(page_result)

        document.status = DocumentStatus.NEEDS_REVIEW
        document.updated_at = utc_now()
        return self.store.save(document, owner_id)

    def _extraction_fingerprint(self, operator_parser: str | None) -> str:
        modal_configured = self._modal_configured()
        capabilities = sorted(
            (
                capability.name,
                capability.version,
                capability.available,
            )
            for capability in self._effective_capabilities(
                modal_configured=modal_configured
            )
        )
        material = {
            "pipeline_contract": "visual-document-extractor-cache-v2",
            "execution_backend": "modal" if modal_configured else "local",
            "operator_parser": operator_parser,
            "capabilities": capabilities,
            "quality_policy": {
                "minimum_confidence": self.router.quality_policy.minimum_confidence,
                "min_text_characters": self.router.quality_policy.min_text_characters,
                "max_replacement_character_ratio": (
                    self.router.quality_policy.max_replacement_character_ratio
                ),
                "max_control_character_ratio": (
                    self.router.quality_policy.max_control_character_ratio
                ),
            },
            "routing_policy": {
                "transient_retries_per_adapter": (
                    self.router.policy.transient_retries_per_adapter
                ),
                "max_alternate_attempts": self.router.policy.max_alternate_attempts,
                "max_vision_attempts": self.router.policy.max_vision_attempts,
            },
        }
        encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return hashlib.sha256(encoded).hexdigest()

    def get(self, document_id: uuid.UUID, owner_id: uuid.UUID) -> DocumentResult:
        return self.store.get(document_id, owner_id)

    def get_source(
        self, document_id: uuid.UUID, owner_id: uuid.UUID
    ) -> tuple[bytes, str, str]:
        return self.store.get_source(document_id, owner_id)

    def delete(self, document_id: uuid.UUID, owner_id: uuid.UUID) -> bool:
        return self.store.delete(document_id, owner_id)

    def review_page(
        self,
        document_id: uuid.UUID,
        page_number: int,
        owner_id: uuid.UUID,
        request: PageReviewRequest,
    ) -> PageResult:
        document = self.store.get(document_id, owner_id)
        page = self._page(document, page_number)
        if page.page_status is PageStatus.FAILED:
            raise InvalidReviewTransitionError("A failed page must be reprocessed")

        by_id = {element.element_id: element for element in page.elements}
        for update in request.elements:
            element = by_id.get(update.element_id)
            if element is None:
                raise InvalidReviewTransitionError(
                    f"Unknown element_id: {update.element_id}"
                )
            element.reviewed_text = update.reviewed_text
        if request.elements:
            page.semantic_result = None

        status_by_action = {
            "save": (PageStatus.NEEDS_REVIEW, ReviewStatus.IN_PROGRESS),
            "approve": (PageStatus.APPROVED, ReviewStatus.APPROVED),
            "reject": (PageStatus.REJECTED, ReviewStatus.REJECTED),
        }
        page.page_status, page.review.status = status_by_action[request.action]
        page.review.reviewer_id = owner_id
        page.review.reviewed_at = utc_now()
        page.audit_events.append(
            AuditEvent(
                event_type=f"review_{request.action}",
                actor_id=owner_id,
                details={
                    "updated_element_ids": [
                        update.element_id for update in request.elements
                    ],
                    "note": request.note,
                },
            )
        )
        self._update_document_status(document)
        document.updated_at = utc_now()
        self.store.save(document, owner_id)
        return page.model_copy(deep=True)

    def reprocess_page(
        self,
        document_id: uuid.UUID,
        page_number: int,
        owner_id: uuid.UUID,
        request: ReprocessRequest,
    ) -> PageResult:
        document = self.store.get(document_id, owner_id)
        page = self._page(document, page_number)
        preserve_current_candidate(page)
        self._validate_parser(request.parser)
        content, media_type, _ = self.store.get_source(document_id, owner_id)
        if page.elements:
            page.extraction_history.append(
                ExtractionSnapshot(
                    parser_run_id=(
                        page.selected_parser.run_id
                        if page.selected_parser is not None
                        else None
                    ),
                    reason="pre_reprocess_review_state",
                    elements=page.elements,
                    warnings=page.warnings,
                )
            )
        outcome = self.router.extract(
            PageInput(
                document_id=document_id,
                page_number=page_number,
                media_type=media_type,
                content=content,
                classification=page.classification,
                signals=page.classification_signals,
                timeout_seconds=self.limits.parser_timeout_seconds,
                operator_parser=request.parser,
            )
        )
        page.semantic_result = None
        page.attempts.extend(outcome.attempts)
        if outcome.manual_review_required or outcome.selected_result is None:
            page.page_status = PageStatus.MANUAL_REVIEW_REQUIRED
        else:
            selected = outcome.selected_result
            add_candidate(
                page,
                selected,
                quality_passed=True,
                rationale=f"Reviewer reprocess: {request.reason}",
            )
            select_best_candidate(page)
            page.extraction_history.append(
                ExtractionSnapshot(
                    parser_run_id=selected.attempt.run_id,
                    reason="reprocess_selected_result",
                    elements=selected.elements,
                    warnings=selected.warnings,
                )
            )
            page.page_status = PageStatus.NEEDS_REVIEW
            page.review.status = ReviewStatus.PENDING
        page.audit_events.append(
            AuditEvent(
                event_type="page_reprocessed",
                actor_id=owner_id,
                details={"parser": request.parser, "reason": request.reason},
            )
        )
        self._update_document_status(document)
        document.updated_at = utc_now()
        self.store.save(document, owner_id)
        return page.model_copy(deep=True)

    @staticmethod
    def _page(document: DocumentResult, page_number: int) -> PageResult:
        for page in document.pages:
            if page.page_number == page_number:
                return page
        raise InvalidPageError("Page not found")

    def _validate_parser(self, parser: str | None) -> None:
        if parser is None:
            return
        supported = {capability.name for capability in self.router.capabilities()}
        if parser not in supported:
            choices = ", ".join(sorted(supported))
            raise InvalidParserOverrideError(
                f"Unsupported parser override {parser!r}; choose from: {choices}"
            )

    @staticmethod
    def _update_document_status(document: DocumentResult) -> None:
        statuses = {page.page_status for page in document.pages}
        if statuses == {PageStatus.APPROVED}:
            document.status = DocumentStatus.APPROVED
        elif PageStatus.REJECTED in statuses:
            document.status = DocumentStatus.REJECTED
        else:
            document.status = DocumentStatus.NEEDS_REVIEW

    @staticmethod
    def _build_page_evidence(validated: ValidatedSource) -> list[PageEvidence]:
        metadata = validated.metadata
        if metadata.media_type == "application/pdf":
            try:
                import fitz  # type: ignore[import-untyped]

                pdf = fitz.open(stream=validated.content, filetype="pdf")
                evidence: list[PageEvidence] = []
                for index, page in enumerate(pdf):
                    native_text = page.get_text("text")
                    blocks = page.get_text("blocks")
                    page_area = max(page.rect.width * page.rect.height, 1)
                    native_text_area = sum(
                        max(block[2] - block[0], 0) * max(block[3] - block[1], 0)
                        for block in blocks
                        if len(block) >= 4
                    )
                    raster_area = 0.0
                    for image in page.get_images(full=True):
                        try:
                            raster_area += sum(
                                max(rect.width, 0) * max(rect.height, 0)
                                for rect in page.get_image_rects(image[0])
                            )
                        except Exception:
                            continue
                    formula_count = len(
                        re.findall(
                            r"(?:[=∑∫√±≤≥]|\b(?:sin|cos|log|lim)\b)",
                            native_text,
                        )
                    )
                    evidence.append(
                        PageEvidence(
                            page_number=index + 1,
                            media_type=metadata.media_type,
                            native_text=native_text,
                            page_area=page_area,
                            native_text_area=min(native_text_area, page_area),
                            raster_area=min(raster_area, page_area),
                            native_text_blocks=len(blocks),
                            layout_regions=len(blocks),
                            formula_count=formula_count,
                            rotation_degrees=page.rotation,
                        )
                    )
                pdf.close()
                return evidence
            except Exception:
                # Intake already established that the PDF is structurally readable.
                pass

        return [
            PageEvidence(
                page_number=page_number,
                media_type=metadata.media_type,
                raster_area=1 if metadata.media_type.startswith("image/") else None,
                page_area=1 if metadata.media_type.startswith("image/") else None,
            )
            for page_number in range(1, metadata.page_count + 1)
        ]

    def _stabilize_office_page_count(self, validated: ValidatedSource) -> None:
        docx_media_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        if validated.metadata.media_type != docx_media_type:
            return
        try:
            pdf_bytes = convert_office_to_pdf(
                validated.content,
                source_name=validated.metadata.source_name,
                media_type=validated.metadata.media_type,
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
            )
            import fitz

            pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
            try:
                if pdf.page_count > 0:
                    if pdf.page_count > self.limits.max_pages:
                        raise IntakeValidationError(
                            IntakeErrorCode.TOO_MANY_PAGES,
                            f"The converted document has {pdf.page_count} pages; "
                            f"the limit is {self.limits.max_pages}.",
                        )
                    validated.metadata.page_count = pdf.page_count
            finally:
                pdf.close()
        except IntakeValidationError:
            raise
        except (PreviewError, OSError, ValueError):
            # Intake already records that DOCX pagination is provisional. The
            # document remains extractable even when preview conversion is absent.
            return


extraction_service = DocumentExtractionService()
