from __future__ import annotations

import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlmodel import SQLModel, create_engine

from app.visual_document_extractor.models import DocumentResult, SourceMetadata
from app.visual_document_extractor.preview import PreviewArtifact
from app.visual_document_extractor.store import (
    ConcurrentDocumentUpdateError,
    DocumentNotFoundError,
    SqlDocumentStore,
    SqlPreviewArtifactCache,
)

OWNER = uuid.UUID("00000000-0000-0000-0000-000000000001")
OTHER_OWNER = uuid.UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture
def sql_store(tmp_path: Path) -> SqlDocumentStore:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'extractor.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    return SqlDocumentStore(engine)


def _document(content: bytes) -> DocumentResult:
    return DocumentResult(
        owner_id=OWNER,
        source=SourceMetadata(
            source_name="durable.png",
            source_sha256=hashlib.sha256(content).hexdigest(),
            media_type="image/png",
            size_bytes=len(content),
            page_count=1,
        ),
        extraction_fingerprint="f" * 64,
    )


def test_document_survives_store_reconstruction_and_is_tenant_scoped(
    sql_store: SqlDocumentStore,
) -> None:
    content = b"immutable-source"
    document = _document(content)
    sql_store.create(document, content)
    restarted = SqlDocumentStore(sql_store.engine)

    loaded = restarted.get(document.document_id, OWNER)
    assert loaded.document_id == document.document_id
    assert restarted.get_source(document.document_id, OWNER)[0] == content
    with pytest.raises(DocumentNotFoundError):
        restarted.get(document.document_id, OTHER_OWNER)


def test_completed_extraction_can_be_loaded_by_source_and_fingerprint(
    sql_store: SqlDocumentStore,
) -> None:
    content = b"immutable-source"
    document = _document(content).model_copy(update={"status": "needs_review"})
    sql_store.create(document, content)

    cached = sql_store.find_cached(
        OWNER,
        document.source.source_sha256,
        document.extraction_fingerprint or "",
    )

    assert cached is not None
    assert cached.document_id == document.document_id
    assert (
        sql_store.find_cached(
            OTHER_OWNER,
            document.source.source_sha256,
            document.extraction_fingerprint or "",
        )
        is None
    )


def test_revision_conflict_prevents_lost_update(sql_store: SqlDocumentStore) -> None:
    content = b"immutable-source"
    document = _document(content)
    sql_store.create(document, content)
    first = sql_store.get(document.document_id, OWNER)
    stale = first.model_copy(deep=True)
    saved = sql_store.save(first, OWNER)
    assert saved.revision == 1
    with pytest.raises(ConcurrentDocumentUpdateError):
        sql_store.save(stale, OWNER)


def test_concurrent_revision_updates_are_atomic(sql_store: SqlDocumentStore) -> None:
    content = b"immutable-source"
    document = _document(content)
    sql_store.create(document, content)
    first = sql_store.get(document.document_id, OWNER)
    second = first.model_copy(deep=True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(
                lambda candidate: _save_outcome(sql_store, candidate),
                [first, second],
            )
        )

    assert sorted(outcomes) == ["conflict", "saved"]


def _save_outcome(store: SqlDocumentStore, document: DocumentResult) -> str:
    try:
        store.save(document, OWNER)
        return "saved"
    except ConcurrentDocumentUpdateError:
        return "conflict"


def test_delete_removes_document_and_preview_artifact(
    sql_store: SqlDocumentStore,
) -> None:
    content = b"immutable-source"
    document = _document(content)
    sql_store.create(document, content)
    cache = SqlPreviewArtifactCache(sql_store.engine, document.document_id)
    artifact = PreviewArtifact(
        content=b"png",
        media_type="image/png",
        width=2,
        height=3,
        page_number=1,
        source_sha256=document.source.source_sha256,
        content_sha256=hashlib.sha256(b"png").hexdigest(),
    )
    cache.put("a" * 64, artifact)
    assert cache.get("a" * 64) == artifact

    assert sql_store.delete(document.document_id, OWNER) is True
    assert cache.get("a" * 64) is None
    with pytest.raises(DocumentNotFoundError):
        sql_store.get(document.document_id, OWNER)


def test_identical_sources_have_tenant_scoped_preview_cache_keys(
    sql_store: SqlDocumentStore,
) -> None:
    content = b"same-source"
    first = _document(content)
    second = _document(content).model_copy(
        update={"document_id": uuid.uuid4(), "owner_id": OTHER_OWNER}
    )
    sql_store.create(first, content)
    sql_store.create(second, content)
    artifact = PreviewArtifact(
        content=b"png",
        media_type="image/png",
        width=1,
        height=1,
        page_number=1,
        source_sha256=first.source.source_sha256,
        content_sha256=hashlib.sha256(b"png").hexdigest(),
    )

    first_cache = SqlPreviewArtifactCache(sql_store.engine, first.document_id)
    second_cache = SqlPreviewArtifactCache(sql_store.engine, second.document_id)
    first_cache.put("b" * 64, artifact)
    second_cache.put("b" * 64, artifact)

    assert first_cache.get("b" * 64) == artifact
    assert second_cache.get("b" * 64) == artifact
