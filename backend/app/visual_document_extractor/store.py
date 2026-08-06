from __future__ import annotations

import hashlib
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol, cast

from sqlalchemy import desc, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import DocumentExtractionRecord, DocumentPreviewArtifactRecord
from app.visual_document_extractor.models import DocumentResult
from app.visual_document_extractor.object_storage import (
    ObjectNotFoundError,
    ObjectStorage,
    ObjectStorageError,
)
from app.visual_document_extractor.preview import PreviewArtifact


class DocumentNotFoundError(LookupError):
    pass


class SourceNotFoundError(LookupError):
    pass


class ConcurrentDocumentUpdateError(RuntimeError):
    pass


class DocumentStore(Protocol):
    def create(self, document: DocumentResult, source: bytes) -> DocumentResult: ...

    def get(self, document_id: uuid.UUID, owner_id: uuid.UUID) -> DocumentResult: ...

    def find_cached(
        self,
        owner_id: uuid.UUID,
        source_sha256: str,
        extraction_fingerprint: str,
    ) -> DocumentResult | None: ...

    def get_source(
        self, document_id: uuid.UUID, owner_id: uuid.UUID
    ) -> tuple[bytes, str, str]: ...

    def save(self, document: DocumentResult, owner_id: uuid.UUID) -> DocumentResult: ...

    def delete(self, document_id: uuid.UUID, owner_id: uuid.UUID) -> bool: ...


@dataclass(frozen=True)
class _StoredSource:
    content: bytes
    media_type: str
    filename: str


class InMemoryDocumentStore:
    """Owner-scoped development store.

    This makes the first slice executable without pretending to be durable. The store
    contract is intentionally small so a database/object-storage implementation can
    replace it without changing service or API contracts.
    """

    def __init__(self) -> None:
        self._documents: dict[uuid.UUID, DocumentResult] = {}
        self._sources: dict[uuid.UUID, _StoredSource] = {}
        self._lock = threading.RLock()

    def create(self, document: DocumentResult, source: bytes) -> DocumentResult:
        with self._lock:
            if document.document_id in self._documents:
                raise ValueError("Document already exists")
            self._documents[document.document_id] = document.model_copy(deep=True)
            self._sources[document.document_id] = _StoredSource(
                content=bytes(source),
                media_type=document.source.media_type,
                filename=document.source.source_name,
            )
            return document.model_copy(deep=True)

    def get(self, document_id: uuid.UUID, owner_id: uuid.UUID) -> DocumentResult:
        with self._lock:
            document = self._documents.get(document_id)
            if document is None or document.owner_id != owner_id:
                # Deliberately conceal whether another tenant owns the identifier.
                raise DocumentNotFoundError("Document not found")
            return document.model_copy(deep=True)

    def find_cached(
        self,
        owner_id: uuid.UUID,
        source_sha256: str,
        extraction_fingerprint: str,
    ) -> DocumentResult | None:
        with self._lock:
            matches = [
                document
                for document in self._documents.values()
                if document.owner_id == owner_id
                and document.source.source_sha256 == source_sha256
                and document.extraction_fingerprint == extraction_fingerprint
                and document.status
                not in {
                    "queued",
                    "classifying",
                    "extracting",
                    "fallback",
                    "failed",
                    "cancelled",
                }
            ]
            if not matches:
                return None
            return max(matches, key=lambda item: item.updated_at).model_copy(deep=True)

    def get_source(
        self, document_id: uuid.UUID, owner_id: uuid.UUID
    ) -> tuple[bytes, str, str]:
        with self._lock:
            self.get(document_id, owner_id)
            source = self._sources.get(document_id)
            if source is None:
                raise SourceNotFoundError("Source not found")
            return bytes(source.content), source.media_type, source.filename

    def save(self, document: DocumentResult, owner_id: uuid.UUID) -> DocumentResult:
        with self._lock:
            current = self._documents.get(document.document_id)
            if current is None or current.owner_id != owner_id:
                raise DocumentNotFoundError("Document not found")
            if document.owner_id != owner_id:
                raise DocumentNotFoundError("Document not found")
            if current.revision != document.revision:
                raise ConcurrentDocumentUpdateError("Document was updated concurrently")
            saved = document.model_copy(update={"revision": document.revision + 1})
            self._documents[document.document_id] = saved.model_copy(deep=True)
            return saved.model_copy(deep=True)

    def delete(self, document_id: uuid.UUID, owner_id: uuid.UUID) -> bool:
        with self._lock:
            document = self._documents.get(document_id)
            if document is None or document.owner_id != owner_id:
                return False
            del self._documents[document_id]
            self._sources.pop(document_id, None)
            return True

    def clear(self) -> None:
        """Test helper; application code must not use this as a deletion API."""
        with self._lock:
            self._documents.clear()
            self._sources.clear()


document_store = InMemoryDocumentStore()


class SqlDocumentStore:
    """Durable PostgreSQL/SQLite store with tenant concealment and revisions."""

    def __init__(
        self,
        engine: Engine,
        *,
        object_storage: ObjectStorage | None = None,
        object_prefix: str = "visual-document-extractor",
        fallback_to_postgres: bool = False,
    ) -> None:
        self.engine = engine
        self.object_storage = object_storage
        self.object_prefix = object_prefix.strip("/")
        self.fallback_to_postgres = fallback_to_postgres

    @property
    def storage_provider(self) -> str:
        return "r2" if self.object_storage is not None else "postgres"

    def _source_key(self, document: DocumentResult) -> str:
        return (
            f"{self.object_prefix}/owners/{document.owner_id}/documents/"
            f"{document.document_id}/source"
        )

    def create(self, document: DocumentResult, source: bytes) -> DocumentResult:
        object_key: str | None = None
        source_bytes: bytes | None = bytes(source)
        if self.object_storage is not None:
            object_key = self._source_key(document)
            try:
                self.object_storage.put(
                    object_key,
                    source,
                    content_type=document.source.media_type,
                    expected_sha256=document.source.source_sha256,
                )
                source_bytes = None
            except ObjectStorageError:
                if not self.fallback_to_postgres:
                    raise
                object_key = None
        record = DocumentExtractionRecord(
            id=document.document_id,
            owner_id=document.owner_id,
            source_name=document.source.source_name,
            source_sha256=document.source.source_sha256,
            extraction_fingerprint=document.extraction_fingerprint,
            media_type=document.source.media_type,
            source_bytes=source_bytes,
            source_storage_provider="r2" if object_key is not None else "postgres",
            source_object_key=object_key,
            normalized_result=document.model_dump(mode="json"),
            revision=document.revision,
            created_at=document.created_at.replace(tzinfo=None),
            updated_at=document.updated_at.replace(tzinfo=None),
        )
        try:
            with Session(self.engine) as session:
                if session.get(DocumentExtractionRecord, document.document_id):
                    raise ValueError("Document already exists")
                session.add(record)
                session.commit()
        except BaseException:
            if object_key is not None and self.object_storage is not None:
                try:
                    self.object_storage.delete(object_key)
                except ObjectStorageError:
                    pass
            raise
        return document.model_copy(deep=True)

    def get(self, document_id: uuid.UUID, owner_id: uuid.UUID) -> DocumentResult:
        with Session(self.engine) as session:
            record = session.exec(
                select(DocumentExtractionRecord).where(
                    DocumentExtractionRecord.id == document_id,
                    DocumentExtractionRecord.owner_id == owner_id,
                )
            ).first()
            if record is None:
                raise DocumentNotFoundError("Document not found")
            payload = dict(record.normalized_result)
            payload["revision"] = record.revision
            return DocumentResult.model_validate(payload)

    def find_cached(
        self,
        owner_id: uuid.UUID,
        source_sha256: str,
        extraction_fingerprint: str,
    ) -> DocumentResult | None:
        columns = cast(Any, DocumentExtractionRecord).__table__.c
        with Session(self.engine) as session:
            record = session.exec(
                select(DocumentExtractionRecord)
                .where(
                    DocumentExtractionRecord.owner_id == owner_id,
                    DocumentExtractionRecord.source_sha256 == source_sha256,
                    DocumentExtractionRecord.extraction_fingerprint
                    == extraction_fingerprint,
                )
                .order_by(desc(columns.updated_at))
            ).first()
            if record is None:
                return None
            payload = dict(record.normalized_result)
            payload["revision"] = record.revision
            document = DocumentResult.model_validate(payload)
            if document.status in {
                "queued",
                "classifying",
                "extracting",
                "fallback",
                "failed",
                "cancelled",
            }:
                return None
            return document

    def get_source(
        self, document_id: uuid.UUID, owner_id: uuid.UUID
    ) -> tuple[bytes, str, str]:
        with Session(self.engine) as session:
            record = session.exec(
                select(DocumentExtractionRecord).where(
                    DocumentExtractionRecord.id == document_id,
                    DocumentExtractionRecord.owner_id == owner_id,
                )
            ).first()
            if record is None:
                raise DocumentNotFoundError("Document not found")
            if record.source_storage_provider == "r2":
                if self.object_storage is None or not record.source_object_key:
                    raise SourceNotFoundError("Source storage is unavailable")
                try:
                    content = self.object_storage.get(
                        record.source_object_key,
                        expected_sha256=record.source_sha256,
                    )
                except (ObjectNotFoundError, ObjectStorageError) as exc:
                    raise SourceNotFoundError("Source storage is unavailable") from exc
            elif record.source_bytes is not None:
                content = bytes(record.source_bytes)
            else:
                raise SourceNotFoundError("Source not found")
            if hashlib.sha256(content).hexdigest() != record.source_sha256:
                raise SourceNotFoundError("Source integrity verification failed")
            return content, record.media_type, record.source_name

    def presign_source(
        self, document_id: uuid.UUID, owner_id: uuid.UUID, *, expires_in: int
    ) -> str | None:
        if self.object_storage is None:
            return None
        with Session(self.engine) as session:
            record = session.exec(
                select(DocumentExtractionRecord).where(
                    DocumentExtractionRecord.id == document_id,
                    DocumentExtractionRecord.owner_id == owner_id,
                )
            ).first()
            if (
                record is None
                or record.source_storage_provider != "r2"
                or not record.source_object_key
            ):
                return None
            return self.object_storage.presign_get(
                record.source_object_key, expires_in=expires_in
            )

    def save(self, document: DocumentResult, owner_id: uuid.UUID) -> DocumentResult:
        if document.owner_id != owner_id:
            raise DocumentNotFoundError("Document not found")
        with Session(self.engine) as session:
            saved = document.model_copy(update={"revision": document.revision + 1})
            columns = cast(Any, DocumentExtractionRecord).__table__.c
            statement = (
                update(DocumentExtractionRecord)
                .where(
                    columns.id == document.document_id,
                    columns.owner_id == owner_id,
                    columns.revision == document.revision,
                )
                .values(
                    normalized_result=saved.model_dump(mode="json"),
                    revision=saved.revision,
                    updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )
            result = cast(Any, session.execute(statement))
            if result.rowcount != 1:
                exists = session.exec(
                    select(DocumentExtractionRecord.id).where(
                        DocumentExtractionRecord.id == document.document_id,
                        DocumentExtractionRecord.owner_id == owner_id,
                    )
                ).first()
                if exists is None:
                    raise DocumentNotFoundError("Document not found")
                raise ConcurrentDocumentUpdateError("Document was updated concurrently")
            session.commit()
            return saved.model_copy(deep=True)

    def delete(self, document_id: uuid.UUID, owner_id: uuid.UUID) -> bool:
        with Session(self.engine) as session:
            record = session.exec(
                select(DocumentExtractionRecord).where(
                    DocumentExtractionRecord.id == document_id,
                    DocumentExtractionRecord.owner_id == owner_id,
                )
            ).first()
            if record is None:
                return False
            artifacts = session.exec(
                select(DocumentPreviewArtifactRecord).where(
                    DocumentPreviewArtifactRecord.document_id == document_id
                )
            ).all()
            object_keys = [
                artifact.object_key
                for artifact in artifacts
                if artifact.storage_provider == "r2" and artifact.object_key
            ]
            if record.source_storage_provider == "r2" and record.source_object_key:
                object_keys.append(record.source_object_key)
            if self.object_storage is not None:
                for object_key in object_keys:
                    self.object_storage.delete(object_key)
            for artifact in artifacts:
                session.delete(artifact)
            session.delete(record)
            session.commit()
        return True


class SqlPreviewArtifactCache:
    def __init__(
        self,
        engine: Engine,
        document_id: uuid.UUID,
        *,
        object_storage: ObjectStorage | None = None,
        object_prefix: str = "visual-document-extractor",
        fallback_to_postgres: bool = False,
    ) -> None:
        self.engine = engine
        self.document_id = document_id
        self.object_storage = object_storage
        self.object_prefix = object_prefix.strip("/")
        self.fallback_to_postgres = fallback_to_postgres

    def _storage_key(self, key: str) -> str:
        return hashlib.sha256(f"{self.document_id}:{key}".encode()).hexdigest()

    def get(self, key: str) -> PreviewArtifact | None:
        with Session(self.engine) as session:
            record = session.get(DocumentPreviewArtifactRecord, self._storage_key(key))
            if record is None:
                return None
            if record.storage_provider == "r2":
                if self.object_storage is None or not record.object_key:
                    return None
                try:
                    content = self.object_storage.get(
                        record.object_key, expected_sha256=record.content_sha256
                    )
                except ObjectStorageError:
                    return None
            elif record.content is not None:
                content = bytes(record.content)
            else:
                return None
            return PreviewArtifact(
                content=content,
                media_type=record.media_type,
                width=record.width,
                height=record.height,
                page_number=record.page_number,
                source_sha256=record.source_sha256,
                content_sha256=record.content_sha256,
            )

    def put(self, key: str, artifact: PreviewArtifact) -> None:
        storage_key = self._storage_key(key)
        object_key: str | None = None
        content: bytes | None = bytes(artifact.content)
        provider = "postgres"
        if self.object_storage is not None:
            object_key = (
                f"{self.object_prefix}/documents/{self.document_id}/previews/"
                f"{storage_key}.png"
            )
            try:
                self.object_storage.put(
                    object_key,
                    artifact.content,
                    content_type=artifact.media_type,
                    expected_sha256=artifact.content_sha256,
                )
                content = None
                provider = "r2"
            except ObjectStorageError:
                if not self.fallback_to_postgres:
                    raise
                object_key = None
        with Session(self.engine) as session:
            existing = session.get(DocumentPreviewArtifactRecord, storage_key)
            if existing is not None:
                return
            session.add(
                DocumentPreviewArtifactRecord(
                    cache_key=storage_key,
                    document_id=self.document_id,
                    page_number=artifact.page_number,
                    media_type=artifact.media_type,
                    width=artifact.width,
                    height=artifact.height,
                    source_sha256=artifact.source_sha256,
                    content_sha256=artifact.content_sha256,
                    content=content,
                    storage_provider=provider,
                    object_key=object_key,
                )
            )
            try:
                session.commit()
            except IntegrityError:
                # A concurrent renderer won the same content-addressed insert.
                session.rollback()
