from __future__ import annotations

import hashlib
import io

import pytest

from app.visual_document_extractor.object_storage import (
    InMemoryObjectStorage,
    ObjectIntegrityError,
    ObjectNotFoundError,
    ObjectStorageError,
    R2ObjectStorage,
    validate_object_key,
)


class FakeR2Client:
    def __init__(self) -> None:
        self.objects: dict[str, dict[str, object]] = {}

    def put_object(self, **kwargs: object) -> dict[str, str]:
        self.objects[str(kwargs["Key"])] = dict(kwargs)
        return {"ETag": '"etag-1"'}

    def get_object(self, **kwargs: object) -> dict[str, object]:
        stored = self.objects[str(kwargs["Key"])]
        payload = bytes(stored["Body"])
        return {
            "Body": io.BytesIO(payload),
            "ContentLength": len(payload),
            "Metadata": stored["Metadata"],
        }

    def delete_object(self, **kwargs: object) -> None:
        self.objects.pop(str(kwargs["Key"]), None)

    def generate_presigned_url(self, operation: str, **kwargs: object) -> str:
        assert operation == "get_object"
        params = kwargs["Params"]
        return f"https://r2.example/{params['Bucket']}/{params['Key']}"


def test_in_memory_round_trip_is_bounded_and_integrity_checked() -> None:
    storage = InMemoryObjectStorage(max_object_bytes=5)
    payload = b"hello"
    digest = hashlib.sha256(payload).hexdigest()

    metadata = storage.put(
        "tenant/document/source.pdf", payload, expected_sha256=digest
    )

    assert metadata.size == 5
    assert metadata.sha256 == digest
    assert storage.get(metadata.key, expected_sha256=digest) == payload
    assert storage.presign_get(metadata.key) is None
    with pytest.raises(ObjectIntegrityError) as mismatch:
        storage.get(metadata.key, expected_sha256="0" * 64)
    assert mismatch.value.code == "checksum_mismatch"
    with pytest.raises(ObjectStorageError) as too_large:
        storage.put("tenant/large", b"123456")
    assert too_large.value.code == "object_too_large"


def test_in_memory_delete_is_idempotent() -> None:
    storage = InMemoryObjectStorage()
    storage.put("tenant/source", b"source")
    storage.delete("tenant/source")
    storage.delete("tenant/source")
    with pytest.raises(ObjectNotFoundError):
        storage.get("tenant/source")


@pytest.mark.parametrize(
    "key", ["", "/absolute", "../escape", "tenant/../escape", "a//b", "a\\b", "a\x00b"]
)
def test_object_keys_reject_unsafe_values(key: str) -> None:
    with pytest.raises(ObjectStorageError) as caught:
        validate_object_key(key)
    assert caught.value.code == "invalid_object_key"


def test_r2_contract_sets_checksum_and_presigns_short_lived_get() -> None:
    client = FakeR2Client()
    storage = R2ObjectStorage(
        bucket="documents",
        endpoint_url="https://account.r2.cloudflarestorage.com",
        client=client,
    )
    payload = b"document"

    metadata = storage.put(
        "tenant/doc/source.pdf", payload, content_type="application/pdf"
    )

    assert client.objects[metadata.key]["Metadata"] == {"sha256": metadata.sha256}
    assert storage.get(metadata.key) == payload
    assert storage.presign_get(metadata.key, expires_in=300).startswith("https://")
    storage.delete(metadata.key)
    assert metadata.key not in client.objects


def test_r2_rejects_corrupt_or_unverifiable_reads() -> None:
    client = FakeR2Client()
    storage = R2ObjectStorage(
        bucket="documents",
        endpoint_url="https://account.r2.cloudflarestorage.com",
        client=client,
    )
    client.objects["tenant/doc"] = {
        "Key": "tenant/doc",
        "Body": b"changed",
        "Metadata": {"sha256": hashlib.sha256(b"original").hexdigest()},
    }
    with pytest.raises(ObjectIntegrityError):
        storage.get("tenant/doc")

    client.objects["tenant/no-checksum"] = {
        "Key": "tenant/no-checksum",
        "Body": b"data",
        "Metadata": {},
    }
    with pytest.raises(ObjectIntegrityError):
        storage.get("tenant/no-checksum")


@pytest.mark.parametrize("expires_in", [0, 59, 3601])
def test_presign_expiry_is_bounded(expires_in: int) -> None:
    storage = R2ObjectStorage(
        bucket="documents",
        endpoint_url="https://account.r2.cloudflarestorage.com",
        client=FakeR2Client(),
    )
    with pytest.raises(ObjectStorageError) as caught:
        storage.presign_get("tenant/doc", expires_in=expires_in)
    assert caught.value.code == "invalid_presign_expiry"


def test_provider_errors_do_not_expose_underlying_secret_message() -> None:
    class BrokenClient(FakeR2Client):
        def put_object(self, **kwargs: object) -> dict[str, str]:
            raise RuntimeError("secret-access-key")

    storage = R2ObjectStorage(
        bucket="documents",
        endpoint_url="https://account.r2.cloudflarestorage.com",
        client=BrokenClient(),
    )
    with pytest.raises(ObjectStorageError) as caught:
        storage.put("tenant/doc", b"data")
    assert caught.value.code == "provider_write_failed"
    assert "secret-access-key" not in str(caught.value)
