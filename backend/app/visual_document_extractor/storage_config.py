from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings

from .object_storage import ObjectStorage, ObjectStorageError, R2ObjectStorage


class StorageConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConfiguredStorage:
    provider: str
    object_storage: ObjectStorage | None
    fallback_reason: str | None = None


def configured_storage() -> ConfiguredStorage:
    if settings.DOCUMENT_EXTRACTOR_STORAGE_PROVIDER == "postgres":
        return ConfiguredStorage(provider="postgres", object_storage=None)
    required = {
        "endpoint": settings.DOCUMENT_EXTRACTOR_R2_ENDPOINT_URL,
        "bucket": settings.DOCUMENT_EXTRACTOR_R2_BUCKET,
        "access_key": settings.DOCUMENT_EXTRACTOR_R2_ACCESS_KEY_ID,
        "secret_key": settings.DOCUMENT_EXTRACTOR_R2_SECRET_ACCESS_KEY,
    }
    missing = sorted(name for name, value in required.items() if not value)
    if missing:
        reason = "R2 configuration is incomplete"
        if settings.DOCUMENT_EXTRACTOR_STORAGE_FALLBACK_TO_POSTGRES:
            return ConfiguredStorage("postgres", None, reason)
        raise StorageConfigurationError(reason)
    try:
        storage = R2ObjectStorage(
            bucket=str(required["bucket"]),
            endpoint_url=str(required["endpoint"]),
            access_key_id=str(required["access_key"]),
            secret_access_key=str(required["secret_key"]),
            max_object_bytes=settings.DOCUMENT_EXTRACTOR_MAX_UPLOAD_BYTES,
            max_presign_seconds=max(60, settings.DOCUMENT_EXTRACTOR_R2_PRESIGN_SECONDS),
        )
    except (ValueError, ObjectStorageError) as exc:
        if settings.DOCUMENT_EXTRACTOR_STORAGE_FALLBACK_TO_POSTGRES:
            return ConfiguredStorage("postgres", None, str(exc))
        raise StorageConfigurationError(str(exc)) from exc
    return ConfiguredStorage(provider="r2", object_storage=storage)
