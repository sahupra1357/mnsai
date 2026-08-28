"""Field extraction must go through Modal when it is configured.

`DocumentExtractionService.ingest` runs the *local* router, which only has the
adapters installed in this image — in practice tesseract. The existing
`/document-extractions` upload hands the work to `ModalExtractionCoordinator`
instead, which is how a digital PDF reaches a digital parser rather than being
rasterised and OCR'd. This feature took the local path, so a text-perfect PDF came
back as OCR output ("Net 30" read as "Net 3@").

These pin the branch, not the parser: which adapter Modal picks is the read-only
pipeline's business.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.contract_fields.service import ContractFieldService, _pages_settled
from app.core.config import settings
from app.visual_document_extractor.models import (
    DocumentResult,
    DocumentStatus,
    ExtractedElement,
    PageResult,
    PageStatus,
    SourceMetadata,
)

OWNER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000aa")


def _document(
    *, page_status: PageStatus, with_text: bool, document_id: uuid.UUID | None = None
) -> DocumentResult:
    elements = (
        [
            ExtractedElement(
                element_id="e1",
                type="paragraph",
                text="Governing Law: State of Delaware",
                reading_order=0,
            )
        ]
        if with_text
        else []
    )
    return DocumentResult(
        document_id=document_id or uuid.uuid4(),
        owner_id=OWNER_ID,
        source=SourceMetadata(
            source_name="msa.pdf",
            source_sha256="a" * 64,
            media_type="application/pdf",
            size_bytes=1024,
            page_count=1,
        ),
        status=DocumentStatus.QUEUED,
        pages=[PageResult(page_number=1, page_status=page_status, elements=elements)],
    )


class _Store:
    """Stands in for `SqlDocumentStore`; `get` is what the wait loop polls."""

    def __init__(self, sequence: list[DocumentResult]) -> None:
        self._sequence = sequence
        self.gets = 0

    def get(self, document_id: uuid.UUID, owner_id: uuid.UUID) -> DocumentResult:
        value = self._sequence[min(self.gets, len(self._sequence) - 1)]
        self.gets += 1
        return value


class _Extraction:
    def __init__(self, store: Any = None) -> None:
        self.store = store
        self.ingest_calls = 0

    def ingest(self, **_kwargs: Any) -> DocumentResult:
        self.ingest_calls += 1
        return _document(page_status=PageStatus.NEEDS_REVIEW, with_text=True)


class _Coordinator:
    def __init__(self, result: DocumentResult) -> None:
        self._result = result
        self.submits = 0

    def submit(self, **_kwargs: Any) -> DocumentResult:
        self.submits += 1
        return self._result


def _service(extraction: _Extraction, coordinator: Any) -> ContractFieldService:
    service = ContractFieldService(extraction)  # type: ignore[arg-type]
    object.__setattr__(service, "_modal_coordinator", lambda: coordinator)
    return service


def test_without_a_coordinator_the_local_path_is_used() -> None:
    extraction = _Extraction()
    service = _service(extraction, None)

    document, warnings = service._ingest(
        owner_id=OWNER_ID, source_name="msa.pdf", content=b"%PDF-1.4"
    )

    assert extraction.ingest_calls == 1
    assert warnings == []
    assert document.pages[0].elements


def test_with_a_coordinator_the_local_path_is_not_used() -> None:
    """The regression: this feature must not quietly extract locally when the other
    upload path would have gone to Modal."""

    settled = _document(page_status=PageStatus.NEEDS_REVIEW, with_text=True)
    extraction = _Extraction()
    coordinator = _Coordinator(settled)
    service = _service(extraction, coordinator)

    document, warnings = service._ingest(
        owner_id=OWNER_ID, source_name="msa.pdf", content=b"%PDF-1.4"
    )

    assert coordinator.submits == 1
    assert extraction.ingest_calls == 0
    assert warnings == []
    assert document.document_id == settled.document_id


def test_a_queued_document_is_waited_for(monkeypatch: pytest.MonkeyPatch) -> None:
    """`submit` returns QUEUED with no elements; reading fields then would blank
    every one of them."""

    document_id = uuid.uuid4()
    queued = _document(
        page_status=PageStatus.PENDING, with_text=False, document_id=document_id
    )
    done = _document(
        page_status=PageStatus.NEEDS_REVIEW, with_text=True, document_id=document_id
    )
    store = _Store([queued, done])
    extraction = _Extraction(store)
    service = _service(extraction, _Coordinator(queued))
    monkeypatch.setattr(settings, "CONTRACT_EXTRACTION_MODAL_POLL_SECONDS", 0.01)
    monkeypatch.setattr(settings, "CONTRACT_EXTRACTION_MODAL_WAIT_SECONDS", 5.0)

    result, warnings = service._ingest(
        owner_id=OWNER_ID, source_name="msa.pdf", content=b"%PDF-1.4"
    )

    assert store.gets >= 2
    assert result.pages[0].elements
    assert warnings == []
    assert extraction.ingest_calls == 0


def test_a_parse_that_never_lands_warns_instead_of_hanging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bounded wait. The record still persists and is raised for a human rather than
    holding the request open for the parser's full timeout."""

    document_id = uuid.uuid4()
    queued = _document(
        page_status=PageStatus.PENDING, with_text=False, document_id=document_id
    )
    extraction = _Extraction(_Store([queued]))
    service = _service(extraction, _Coordinator(queued))
    monkeypatch.setattr(settings, "CONTRACT_EXTRACTION_MODAL_POLL_SECONDS", 0.01)
    monkeypatch.setattr(settings, "CONTRACT_EXTRACTION_MODAL_WAIT_SECONDS", 0.05)

    result, warnings = service._ingest(
        owner_id=OWNER_ID, source_name="msa.pdf", content=b"%PDF-1.4"
    )

    assert not result.pages[0].elements
    assert warnings and "did not finish" in warnings[0]
    # Never a second, separately billed local extraction for the same upload.
    assert extraction.ingest_calls == 0


@pytest.mark.parametrize(
    ("statuses", "settled"),
    [
        ([PageStatus.PENDING], False),
        ([PageStatus.EXTRACTING], False),
        ([PageStatus.NEEDS_REVIEW], True),
        ([PageStatus.APPROVED, PageStatus.PENDING], False),
        ([PageStatus.NEEDS_REVIEW, PageStatus.FAILED], True),
    ],
)
def test_pages_settled_matches_the_callbacks_rule(
    statuses: list[PageStatus], settled: bool
) -> None:
    """The same condition the Modal callback uses to mark a document complete."""

    document = _document(page_status=PageStatus.PENDING, with_text=False)
    document.pages = [
        PageResult(page_number=index + 1, page_status=status)
        for index, status in enumerate(statuses)
    ]

    assert _pages_settled(document) is settled


def test_a_service_without_a_store_stays_local() -> None:
    """A stand-in extraction service must not reach for remote execution."""

    service = ContractFieldService(_Extraction())  # type: ignore[arg-type]

    assert service._modal_coordinator() is None
