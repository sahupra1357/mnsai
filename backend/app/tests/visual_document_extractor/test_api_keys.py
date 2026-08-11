from __future__ import annotations

import uuid
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from app.models import DocumentExtractionApiKeyRecord
from app.visual_document_extractor.api_keys import ApiKeyRepository


def test_api_key_plaintext_is_returned_once_hashed_and_revocable(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'keys.db'}")
    SQLModel.metadata.create_all(engine)
    repository = ApiKeyRepository(engine)
    owner_id = uuid.uuid4()

    created = repository.create(owner_id, "automation")

    assert created.api_key.startswith("mnsai_")
    assert repository.authenticate(created.api_key) == owner_id
    with Session(engine) as session:
        stored = session.exec(select(DocumentExtractionApiKeyRecord)).one()
        assert stored.key_hash != created.api_key
        assert created.api_key not in stored.key_hash
        assert stored.last_used_at is not None

    assert repository.revoke(owner_id, created.id) is True
    assert repository.authenticate(created.api_key) is None


def test_rotation_atomically_revokes_old_key_and_returns_replacement(
    tmp_path: Path,
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'rotation.db'}")
    SQLModel.metadata.create_all(engine)
    repository = ApiKeyRepository(engine)
    owner_id = uuid.uuid4()
    created = repository.create(owner_id, "production integration")

    replacement = repository.rotate(owner_id, created.id)

    assert replacement is not None
    assert replacement.id != created.id
    assert replacement.name == created.name
    assert replacement.api_key != created.api_key
    assert repository.authenticate(created.api_key) is None
    assert repository.authenticate(replacement.api_key) == owner_id
    assert repository.rotate(owner_id, created.id) is None
    assert repository.rotate(uuid.uuid4(), replacement.id) is None
