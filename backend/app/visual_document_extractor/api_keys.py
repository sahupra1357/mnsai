from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.models import DocumentExtractionApiKeyRecord


class ApiKeyCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=100)


class ApiKeyMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    key_prefix: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class ApiKeyCreated(ApiKeyMetadata):
    api_key: str


class ApiKeyRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def _new_record(
        self, owner_id: uuid.UUID, name: str
    ) -> tuple[DocumentExtractionApiKeyRecord, str]:
        value = f"mnsai_{secrets.token_urlsafe(32)}"
        return (
            DocumentExtractionApiKeyRecord(
                owner_id=owner_id,
                name=name.strip(),
                key_prefix=value[:14],
                key_hash=self._hash(value),
            ),
            value,
        )

    @staticmethod
    def _created(
        record: DocumentExtractionApiKeyRecord, value: str
    ) -> ApiKeyCreated:
        return ApiKeyCreated(
            **ApiKeyMetadata.model_validate(record).model_dump(), api_key=value
        )

    def create(self, owner_id: uuid.UUID, name: str) -> ApiKeyCreated:
        record, value = self._new_record(owner_id, name)
        with Session(self.engine) as session:
            session.add(record)
            session.commit()
            session.refresh(record)
        return self._created(record, value)

    def list(self, owner_id: uuid.UUID) -> list[ApiKeyMetadata]:
        with Session(self.engine) as session:
            records = session.exec(
                select(DocumentExtractionApiKeyRecord)
                .where(DocumentExtractionApiKeyRecord.owner_id == owner_id)
            ).all()
        return [
            ApiKeyMetadata.model_validate(record)
            for record in sorted(records, key=lambda item: item.created_at, reverse=True)
        ]

    def revoke(self, owner_id: uuid.UUID, key_id: uuid.UUID) -> bool:
        with Session(self.engine) as session:
            record = session.exec(
                select(DocumentExtractionApiKeyRecord).where(
                    DocumentExtractionApiKeyRecord.id == key_id,
                    DocumentExtractionApiKeyRecord.owner_id == owner_id,
                )
            ).first()
            if record is None:
                return False
            if record.revoked_at is None:
                record.revoked_at = self._now()
                session.add(record)
                session.commit()
            return True

    def rotate(
        self, owner_id: uuid.UUID, key_id: uuid.UUID
    ) -> ApiKeyCreated | None:
        """Atomically revoke an active key and issue its named replacement."""
        with Session(self.engine) as session:
            current = session.exec(
                select(DocumentExtractionApiKeyRecord)
                .where(
                    DocumentExtractionApiKeyRecord.id == key_id,
                    DocumentExtractionApiKeyRecord.owner_id == owner_id,
                )
                .with_for_update()
            ).first()
            if current is None or current.revoked_at is not None:
                return None
            replacement, value = self._new_record(owner_id, current.name)
            current.revoked_at = self._now()
            session.add(current)
            session.add(replacement)
            session.commit()
            session.refresh(replacement)
        return self._created(replacement, value)

    def authenticate(self, candidate: str) -> uuid.UUID | None:
        digest = self._hash(candidate)
        with Session(self.engine) as session:
            record = session.exec(
                select(DocumentExtractionApiKeyRecord).where(
                    DocumentExtractionApiKeyRecord.key_hash == digest,
                )
            ).first()
            if (
                record is None
                or record.revoked_at is not None
                or not secrets.compare_digest(record.key_hash, digest)
            ):
                return None
            record.last_used_at = self._now()
            session.add(record)
            session.commit()
            return record.owner_id
