from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DocumentStatus(str, Enum):
    QUEUED = "queued"
    CLASSIFYING = "classifying"
    EXTRACTING = "extracting"
    FALLBACK = "fallback"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PageStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    FAILED = "failed"


class PageClassification(str, Enum):
    DIGITAL = "digital"
    SCANNED = "scanned"
    FORMULA_HEAVY = "formula_heavy"
    COMPLEX_LAYOUT = "complex_layout"
    UNKNOWN = "unknown"


class AttemptStatus(str, Enum):
    SUCCEEDED = "succeeded"
    LOW_CONFIDENCE = "low_confidence"
    FAILED = "failed"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"


class CoordinateSpace(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    width: float = Field(gt=0)
    height: float = Field(gt=0)
    origin: Literal["top-left"] = "top-left"


class BoundingBox(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    left: float
    top: float
    right: float
    bottom: float

    def as_list(self) -> list[float]:
        return [self.left, self.top, self.right, self.bottom]

    @model_validator(mode="after")
    def validate_order(self) -> BoundingBox:
        if self.right < self.left or self.bottom < self.top:
            raise ValueError("Bounding-box coordinates are not ordered")
        return self


class QualitySignal(BaseModel):
    name: str
    passed: bool | None = None
    value: float | int | str | bool | None = None
    threshold: float | int | str | bool | None = None
    detail: str | None = None


class ClassificationSignals(BaseModel):
    native_text_characters: int = Field(default=0, ge=0)
    native_text_density: float | None = Field(default=None, ge=0)
    raster_coverage: float | None = Field(default=None, ge=0, le=1)
    replacement_character_ratio: float | None = Field(default=None, ge=0, le=1)
    formula_score: float = Field(default=0, ge=0, le=1)
    complex_layout_score: float = Field(default=0, ge=0, le=1)
    scientific_score: float = Field(default=0, ge=0, le=1)
    rotation_degrees: int = 0
    reasons: list[str] = Field(default_factory=list)


class PageInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    document_id: uuid.UUID
    page_number: int = Field(ge=1)
    media_type: str
    content: bytes = Field(repr=False)
    classification: PageClassification
    signals: ClassificationSignals = Field(default_factory=ClassificationSignals)
    coordinate_space: CoordinateSpace | None = None
    timeout_seconds: float = Field(default=60, gt=0)
    operator_parser: str | None = None
    fallback_context: list[dict[str, Any]] = Field(default_factory=list)


class ExtractedElement(BaseModel):
    element_id: str
    type: Literal[
        "paragraph",
        "heading",
        "table",
        "table_cell",
        "formula",
        "list_item",
        "image_description",
        "field",
        "other",
    ] = "paragraph"
    text: str
    reviewed_text: str | None = None
    bounding_box: BoundingBox | None = None
    coordinate_space: CoordinateSpace | None = None
    reading_order: int = Field(ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    confidence_source: str | None = None
    model_derived: bool = False
    source_block_number: int | None = Field(default=None, ge=0)
    source_paragraph_number: int | None = Field(default=None, ge=0)
    source_line_number: int | None = Field(default=None, ge=0)
    source_word_number: int | None = Field(default=None, ge=0)


class ParserSelection(BaseModel):
    name: str
    version: str
    run_id: uuid.UUID
    rationale: str


class ExtractionAttempt(BaseModel):
    parser: str
    version: str
    run_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    status: AttemptStatus
    confidence: float | None = Field(default=None, ge=0, le=1)
    quality_signals: list[QualitySignal] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False
    raw_output_ref: str | None = None
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime = Field(default_factory=utc_now)


class AdapterResult(BaseModel):
    attempt: ExtractionAttempt
    elements: list[ExtractedElement] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AdapterCapability(BaseModel):
    name: str
    version: str | None = None
    available: bool
    reason: str | None = None
    classifications: list[PageClassification] = Field(default_factory=list)


class ReviewState(BaseModel):
    status: ReviewStatus = ReviewStatus.PENDING
    reviewer_id: uuid.UUID | None = None
    reviewed_at: datetime | None = None


class AuditEvent(BaseModel):
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_type: str
    actor_id: uuid.UUID | None = None
    occurred_at: datetime = Field(default_factory=utc_now)
    details: dict[str, Any] = Field(default_factory=dict)


class ExtractionSnapshot(BaseModel):
    snapshot_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    parser_run_id: uuid.UUID | None = None
    reason: str
    elements: list[ExtractedElement] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    captured_at: datetime = Field(default_factory=utc_now)


class ExtractionCandidate(BaseModel):
    candidate_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    parser: ParserSelection
    confidence: float | None = Field(default=None, ge=0, le=1)
    confidence_source: str | None = None
    quality_passed: bool = False
    elements: list[ExtractedElement] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class PageResult(BaseModel):
    page_number: int = Field(ge=1)
    page_status: PageStatus = PageStatus.PENDING
    confidence: float | None = Field(default=None, ge=0, le=1)
    confidence_source: str | None = None
    classification: PageClassification = PageClassification.UNKNOWN
    classification_signals: ClassificationSignals = Field(
        default_factory=ClassificationSignals
    )
    routing_reasons: list[str] = Field(default_factory=list)
    selected_parser: ParserSelection | None = None
    attempts: list[ExtractionAttempt] = Field(default_factory=list)
    elements: list[ExtractedElement] = Field(default_factory=list)
    semantic_result: dict[str, Any] | None = None
    candidates: list[ExtractionCandidate] = Field(default_factory=list)
    selected_candidate_id: uuid.UUID | None = None
    extraction_history: list[ExtractionSnapshot] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    review: ReviewState = Field(default_factory=ReviewState)
    audit_events: list[AuditEvent] = Field(default_factory=list)


class SourceMetadata(BaseModel):
    source_name: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    media_type: str
    size_bytes: int = Field(gt=0)
    page_count: int = Field(ge=1)


class DocumentResult(BaseModel):
    document_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    owner_id: uuid.UUID
    source: SourceMetadata
    status: DocumentStatus = DocumentStatus.QUEUED
    extraction_fingerprint: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    reused_extraction: bool = False
    pages: list[PageResult] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    revision: int = Field(default=0, ge=0)


class ReviewElementUpdate(BaseModel):
    element_id: str
    reviewed_text: str


class PageReviewRequest(BaseModel):
    action: Literal["save", "approve", "reject"]
    elements: list[ReviewElementUpdate] = Field(default_factory=list)
    note: str | None = Field(default=None, max_length=2000)


class ReprocessRequest(BaseModel):
    parser: str | None = None
    reason: str = Field(min_length=1, max_length=1000)


class CapabilityResponse(BaseModel):
    adapters: list[AdapterCapability]
    supported_extensions: list[str]
    max_upload_bytes: int
    max_pages: int
    retry_limits: dict[str, int]
    storage_provider: str = "postgres"
    execution_backend: str = "local"
    modal_enabled: bool = False
