"""Orchestration: extract -> ground -> normalize -> classify -> persist.

One request does all of it. The existing visual extractor produces (or reuses) the
document's elements; this service turns them into the ten-key payload, decides the
outcome, writes the row, and returns it.

Two rules shape every branch here:

* **Blank beats a guess.** A value that cannot be grounded in a source element, or
  cannot be normalized to its field's format, is ``""`` with a specific reason —
  never a plausible-looking value.
* **A failure is still a result.** `needs_verification` persists and returns 200. The
  row is what the human works from, so withholding it would be the actual failure.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlmodel import Session

from app.models import ContractFieldExtractionRecord
from app.visual_document_extractor.models import DocumentResult
from app.visual_document_extractor.service import DocumentExtractionService

from . import store
from .catalogue import FIELD_BY_KEY, ValueFormat, assemble_fields, requested_field_keys
from .extractor import CandidateSet, FieldCandidate, propose_candidates
from .grounding import ground_value
from .models import (
    ContractFieldRecordRow,
    ContractFieldResult,
    ContractFields,
    ExtractionStatus,
    FieldProvenance,
    UnresolvedReason,
)
from .normalize import normalize_field_value
from .verification import classify_outcome


class FieldExtractionOutcome:
    """The per-field working state between grounding and classification."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.reasons: dict[str, UnresolvedReason] = {}
        self.provenance: list[FieldProvenance] = []
        self.warnings: list[str] = []


def _ground_candidate(
    candidate: FieldCandidate,
    document: DocumentResult,
) -> tuple[list[str], list[FieldProvenance], str | None]:
    """Verify every value the candidate proposes against the page it cites.

    Returns the accepted values, their provenance, and a rejection detail when
    nothing survived.
    """

    page = next(
        (item for item in document.pages if item.page_number == candidate.page_number),
        None,
    )
    elements = list(page.elements) if page is not None else []
    accepted: list[str] = []
    provenance: list[FieldProvenance] = []
    detail: str | None = None
    for order, value in enumerate(candidate.values):
        verdict = ground_value(
            candidate.field_key,
            value,
            candidate.source_element_ids,
            elements,
            source_order=order,
        )
        if not verdict.accepted:
            detail = verdict.detail or verdict.status.value
            continue
        accepted.append(verdict.value)
        provenance.append(
            FieldProvenance(
                field_key=candidate.field_key,
                page_number=candidate.page_number,
                source_element_ids=verdict.source_element_ids,
                grounding_status=verdict.status,
                confidence=candidate.confidence,
            )
        )
    return accepted, provenance, detail


def resolve_fields(
    document: DocumentResult,
    requested: Sequence[str],
    proposals: CandidateSet,
) -> FieldExtractionOutcome:
    """Ground and normalize every requested field, recording why each blank is blank."""

    outcome = FieldExtractionOutcome()
    outcome.warnings.extend(proposals.warnings)

    for key in requested:
        candidate = proposals.candidates.get(key)
        if candidate is None:
            outcome.values[key] = ""
            outcome.reasons[key] = (
                UnresolvedReason.PROVIDER_UNAVAILABLE
                if not proposals.provider_available
                else UnresolvedReason.NOT_FOUND
            )
            continue

        accepted, provenance, detail = _ground_candidate(candidate, document)
        if not accepted:
            outcome.values[key] = ""
            outcome.reasons[key] = UnresolvedReason.UNGROUNDED
            outcome.warnings.append(
                f"{key}: a proposed value was not supported by its cited source "
                f"({detail or 'ungrounded'}) and was discarded."
            )
            continue

        raw: object = accepted if key == "parties" else accepted[0]
        normalized = normalize_field_value(key, raw)
        if not normalized:
            outcome.values[key] = ""
            outcome.reasons[key] = UnresolvedReason.NORMALIZATION_FAILED
            definition = FIELD_BY_KEY[key]
            expected = (
                "DD/MM/YYYY"
                if definition.value_format is ValueFormat.DATE_DDMMYYYY
                else "<CURRENCY> <amount>"
                if definition.value_format is ValueFormat.CURRENCY_AMOUNT
                else definition.value_format.value
            )
            outcome.warnings.append(
                f"{key}: {accepted[0]!r} could not be normalized to {expected}; "
                "left blank for verification."
            )
            continue

        outcome.values[key] = normalized
        outcome.provenance.extend(provenance)

    return outcome


def to_result(record: ContractFieldExtractionRecord) -> ContractFieldResult:
    """The stored row as the API's response shape — ten keys, always."""

    return ContractFieldResult(
        extraction_id=record.id,
        document_id=record.document_id,
        fields=ContractFields(**store.machine_fields(record)),
        selected_fields=list(record.selected_fields or []),
        extraction_status=ExtractionStatus(record.extraction_status),
        unresolved_fields=list(record.unresolved_fields or []),  # type: ignore[arg-type]
        field_provenance=list(record.field_provenance or []),  # type: ignore[arg-type]
        warnings=list(record.warnings or []),
        verified_values=dict(record.verified_values or {}),
        created_at=record.created_at,
    )


def to_row(record: ContractFieldExtractionRecord) -> ContractFieldRecordRow:
    """The stored row as one line of the table view.

    Carries the machine values and the human overlay separately so the table can
    show the effective value and still mark which cells a human supplied.
    """

    return ContractFieldRecordRow(
        extraction_id=record.id,
        document_id=record.document_id,
        source_name=record.source_name,
        fields=ContractFields(**store.machine_fields(record)),
        selected_fields=list(record.selected_fields or []),
        extraction_status=ExtractionStatus(record.extraction_status),
        unresolved_fields=list(record.unresolved_fields or []),  # type: ignore[arg-type]
        verified_values=dict(record.verified_values or {}),
        verified_by=record.verified_by,
        verified_at=record.verified_at,
        created_at=record.created_at,
    )


class ContractFieldService:
    """Runs one extraction end to end."""

    def __init__(self, extraction_service: DocumentExtractionService) -> None:
        self._extraction = extraction_service

    def extract(
        self,
        session: Session,
        *,
        owner_id: uuid.UUID,
        source_name: str,
        content: bytes,
        selected_fields: Sequence[str],
        use_provider: bool = True,
    ) -> ContractFieldResult:
        """Upload -> ten-key JSON -> one persisted row.

        The document extraction itself is the existing pipeline's job, reused
        untouched: a document already extracted for this owner comes back from its
        cache rather than being parsed again.
        """

        document = self._extraction.ingest(
            owner_id=owner_id, source_name=source_name, content=content
        )
        requested = requested_field_keys(selected_fields)
        proposals = propose_candidates(
            document, list(requested), use_provider=use_provider
        )
        outcome = resolve_fields(document, requested, proposals)

        fields = assemble_fields(outcome.values, requested_keys=requested)
        status, unresolved = classify_outcome(
            fields, list(selected_fields), outcome.reasons
        )
        record = store.insert_extraction(
            session,
            owner_id=owner_id,
            document_id=document.document_id,
            source_name=document.source.source_name,
            source_sha256=document.source.source_sha256,
            fields=fields,
            selected_fields=list(selected_fields),
            extraction_status=status,
            unresolved_fields=[entry.model_dump(mode="json") for entry in unresolved],
            field_provenance=[
                entry.model_dump(mode="json") for entry in outcome.provenance
            ],
            warnings=outcome.warnings,
        )
        return to_result(record)

    def get_source(
        self, document_id: uuid.UUID, owner_id: uuid.UUID
    ) -> tuple[bytes, str, str]:
        """The stored source bytes for the left-hand document pane."""

        return self._extraction.get_source(document_id, owner_id)
