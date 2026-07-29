import uuid

import pytest
from pydantic import ValidationError

from app.visual_document_extractor.models import (
    BoundingBox,
    CoordinateSpace,
    DocumentResult,
    SourceMetadata,
)
from app.visual_document_extractor.store import (
    DocumentNotFoundError,
    InMemoryDocumentStore,
)

OWNER_A = uuid.UUID("00000000-0000-0000-0000-000000000001")
OWNER_B = uuid.UUID("00000000-0000-0000-0000-000000000002")


def make_document(owner_id: uuid.UUID = OWNER_A) -> DocumentResult:
    return DocumentResult(
        owner_id=owner_id,
        source=SourceMetadata(
            source_name="sample.pdf",
            source_sha256="a" * 64,
            media_type="application/pdf",
            size_bytes=12,
            page_count=1,
        ),
    )


def test_bounding_box_rejects_reversed_coordinates() -> None:
    with pytest.raises(ValidationError):
        BoundingBox(left=10, top=0, right=2, bottom=20)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: BoundingBox(left=float("nan"), top=0, right=2, bottom=20),
        lambda: CoordinateSpace(width=float("inf"), height=20),
    ],
)
def test_geometry_rejects_non_finite_coordinates(factory) -> None:
    with pytest.raises(ValidationError):
        factory()


def test_store_conceals_cross_tenant_documents() -> None:
    store = InMemoryDocumentStore()
    document = make_document()
    store.create(document, b"%PDF-source")

    with pytest.raises(DocumentNotFoundError):
        store.get(document.document_id, OWNER_B)
    with pytest.raises(DocumentNotFoundError):
        store.get_source(document.document_id, OWNER_B)


def test_store_returns_deep_copies_and_immutable_source_bytes() -> None:
    store = InMemoryDocumentStore()
    document = make_document()
    store.create(document, b"%PDF-source")

    fetched = store.get(document.document_id, OWNER_A)
    fetched.status = "failed"  # type: ignore[assignment]

    unchanged = store.get(document.document_id, OWNER_A)
    assert unchanged.status.value == "queued"
    content, media_type, filename = store.get_source(document.document_id, OWNER_A)
    assert content == b"%PDF-source"
    assert media_type == "application/pdf"
    assert filename == "sample.pdf"


def test_cached_document_is_tenant_and_fingerprint_scoped() -> None:
    store = InMemoryDocumentStore()
    fingerprint = "f" * 64
    document = make_document().model_copy(
        update={
            "status": "needs_review",
            "extraction_fingerprint": fingerprint,
        }
    )
    store.create(document, b"%PDF-source")

    assert (
        store.find_cached(
            OWNER_A, document.source.source_sha256, fingerprint
        )
        is not None
    )
    assert (
        store.find_cached(
            OWNER_B, document.source.source_sha256, fingerprint
        )
        is None
    )
    assert (
        store.find_cached(
            OWNER_A, document.source.source_sha256, "e" * 64
        )
        is None
    )
