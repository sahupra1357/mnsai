from __future__ import annotations

import hashlib
import importlib
import re
import threading
from dataclasses import dataclass
from typing import Any, Protocol

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ObjectStorageError(RuntimeError):
    """Safe, structured storage failure suitable for an API error boundary."""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class ObjectNotFoundError(ObjectStorageError):
    def __init__(self) -> None:
        super().__init__("object_not_found", "Stored object was not found")


class ObjectIntegrityError(ObjectStorageError):
    def __init__(self) -> None:
        super().__init__(
            "checksum_mismatch", "Stored object failed its integrity check"
        )


@dataclass(frozen=True)
class ObjectMetadata:
    key: str
    size: int
    sha256: str
    etag: str | None = None


class ObjectStorage(Protocol):
    def put(
        self,
        key: str,
        content: bytes,
        *,
        content_type: str = "application/octet-stream",
        expected_sha256: str | None = None,
    ) -> ObjectMetadata: ...

    def get(self, key: str, *, expected_sha256: str | None = None) -> bytes: ...

    def delete(self, key: str) -> None: ...

    def presign_get(self, key: str, *, expires_in: int = 900) -> str | None: ...


def validate_object_key(key: str) -> str:
    if not isinstance(key, str) or not key or len(key.encode("utf-8")) > 1024:
        raise ObjectStorageError("invalid_object_key", "Object key is invalid")
    if (
        key.startswith("/")
        or "\\" in key
        or any(part in {"", ".", ".."} for part in key.split("/"))
    ):
        raise ObjectStorageError("invalid_object_key", "Object key is invalid")
    if any(ord(character) < 32 or ord(character) == 127 for character in key):
        raise ObjectStorageError("invalid_object_key", "Object key is invalid")
    return key


def _validate_sha256(value: str | None) -> str | None:
    if value is not None and not _SHA256_RE.fullmatch(value):
        raise ObjectStorageError("invalid_checksum", "SHA-256 checksum is invalid")
    return value


def _validate_expiry(expires_in: int, maximum: int) -> int:
    if isinstance(expires_in, bool) or not 60 <= expires_in <= maximum:
        raise ObjectStorageError(
            "invalid_presign_expiry",
            f"Presigned URL expiry must be between 60 and {maximum} seconds",
        )
    return expires_in


class InMemoryObjectStorage:
    """Bounded test/development provider; it cannot issue reachable signed URLs."""

    def __init__(self, *, max_object_bytes: int = 100 * 1024 * 1024) -> None:
        if max_object_bytes <= 0:
            raise ValueError("max_object_bytes must be positive")
        self.max_object_bytes = max_object_bytes
        self._objects: dict[str, tuple[bytes, str, str]] = {}
        self._lock = threading.RLock()

    def put(
        self,
        key: str,
        content: bytes,
        *,
        content_type: str = "application/octet-stream",
        expected_sha256: str | None = None,
    ) -> ObjectMetadata:
        key = validate_object_key(key)
        expected_sha256 = _validate_sha256(expected_sha256)
        payload = bytes(content)
        if len(payload) > self.max_object_bytes:
            raise ObjectStorageError("object_too_large", "Object exceeds storage limit")
        digest = hashlib.sha256(payload).hexdigest()
        if expected_sha256 is not None and digest != expected_sha256:
            raise ObjectIntegrityError()
        with self._lock:
            self._objects[key] = (payload, content_type, digest)
        return ObjectMetadata(key=key, size=len(payload), sha256=digest)

    def get(self, key: str, *, expected_sha256: str | None = None) -> bytes:
        key = validate_object_key(key)
        expected_sha256 = _validate_sha256(expected_sha256)
        with self._lock:
            stored = self._objects.get(key)
        if stored is None:
            raise ObjectNotFoundError()
        payload, _content_type, stored_digest = stored
        digest = hashlib.sha256(payload).hexdigest()
        if digest != stored_digest or (
            expected_sha256 is not None and digest != expected_sha256
        ):
            raise ObjectIntegrityError()
        return bytes(payload)

    def delete(self, key: str) -> None:
        key = validate_object_key(key)
        with self._lock:
            self._objects.pop(key, None)

    def presign_get(self, key: str, *, expires_in: int = 900) -> None:
        validate_object_key(key)
        _validate_expiry(expires_in, 3600)
        return None


class R2ObjectStorage:
    """Cloudflare R2 provider using its S3-compatible API.

    boto3 remains an optional dependency and is imported only when a client is not
    supplied. Injecting a client keeps contract tests independent of cloud access.
    """

    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: str,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        client: Any | None = None,
        max_object_bytes: int = 100 * 1024 * 1024,
        max_presign_seconds: int = 3600,
    ) -> None:
        if not bucket or not endpoint_url.startswith("https://"):
            raise ValueError("R2 bucket and HTTPS endpoint_url are required")
        if max_object_bytes <= 0 or max_presign_seconds < 60:
            raise ValueError("R2 storage limits are invalid")
        self.bucket = bucket
        self.max_object_bytes = max_object_bytes
        self.max_presign_seconds = max_presign_seconds
        if client is None:
            if not access_key_id or not secret_access_key:
                raise ValueError("R2 credentials are required")
            try:
                boto3 = importlib.import_module("boto3")
            except ImportError:
                raise ObjectStorageError(
                    "provider_unavailable",
                    "R2 storage requires the optional boto3 dependency",
                ) from None
            client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name="auto",
            )
        self._client = client

    def put(
        self,
        key: str,
        content: bytes,
        *,
        content_type: str = "application/octet-stream",
        expected_sha256: str | None = None,
    ) -> ObjectMetadata:
        key = validate_object_key(key)
        expected_sha256 = _validate_sha256(expected_sha256)
        payload = bytes(content)
        if len(payload) > self.max_object_bytes:
            raise ObjectStorageError("object_too_large", "Object exceeds storage limit")
        digest = hashlib.sha256(payload).hexdigest()
        if expected_sha256 is not None and digest != expected_sha256:
            raise ObjectIntegrityError()
        try:
            response = self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=payload,
                ContentType=content_type,
                Metadata={"sha256": digest},
            )
        except Exception:
            raise ObjectStorageError(
                "provider_write_failed", "Object storage write failed", retryable=True
            ) from None
        etag = response.get("ETag")
        return ObjectMetadata(
            key=key,
            size=len(payload),
            sha256=digest,
            etag=etag.strip('"') if isinstance(etag, str) else None,
        )

    def get(self, key: str, *, expected_sha256: str | None = None) -> bytes:
        key = validate_object_key(key)
        expected_sha256 = _validate_sha256(expected_sha256)
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
        except Exception as error:
            response_code = getattr(error, "response", {}).get("Error", {}).get("Code")
            if response_code in {"NoSuchKey", "404", "NotFound"}:
                raise ObjectNotFoundError() from None
            raise ObjectStorageError(
                "provider_read_failed", "Object storage read failed", retryable=True
            ) from None
        length = response.get("ContentLength")
        body = response.get("Body")
        if body is None or (isinstance(length, int) and length > self.max_object_bytes):
            if body is not None and hasattr(body, "close"):
                body.close()
            raise ObjectStorageError("object_too_large", "Object exceeds storage limit")
        try:
            payload = body.read(self.max_object_bytes + 1)
        except Exception:
            raise ObjectStorageError(
                "provider_read_failed", "Object storage read failed", retryable=True
            ) from None
        finally:
            if hasattr(body, "close"):
                body.close()
        if len(payload) > self.max_object_bytes:
            raise ObjectStorageError("object_too_large", "Object exceeds storage limit")
        digest = hashlib.sha256(payload).hexdigest()
        stored_digest = response.get("Metadata", {}).get("sha256")
        checksum = expected_sha256 or stored_digest
        if checksum is None or not _SHA256_RE.fullmatch(checksum) or digest != checksum:
            raise ObjectIntegrityError()
        return bytes(payload)

    def delete(self, key: str) -> None:
        key = validate_object_key(key)
        try:
            self._client.delete_object(Bucket=self.bucket, Key=key)
        except Exception:
            raise ObjectStorageError(
                "provider_delete_failed",
                "Object storage deletion failed",
                retryable=True,
            ) from None

    def presign_get(self, key: str, *, expires_in: int = 900) -> str:
        key = validate_object_key(key)
        expires_in = _validate_expiry(expires_in, self.max_presign_seconds)
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except Exception:
            raise ObjectStorageError(
                "presign_failed", "Could not create object download URL", retryable=True
            ) from None
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ObjectStorageError(
                "presign_failed", "Could not create object download URL"
            )
        return url
