"""Security and HTTP contracts for dispatching extraction work to Modal.

This module deliberately does not persist credentials.  Callers persist ``token_id``
and ``token_hash`` from :class:`OpaqueToken`, then pass the plaintext token only in the
one outbound dispatch request that needs it.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr


@dataclass(frozen=True, repr=False)
class OpaqueToken:
    """New opaque credential and its safe-to-persist metadata."""

    token_id: str
    token: str
    token_hash: str

    def __repr__(self) -> str:
        return f"OpaqueToken(token_id={self.token_id!r}, token=<redacted>)"


def hash_opaque_token(token: str) -> str:
    """Return the canonical digest stored for an opaque token."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_opaque_token(*, entropy_bytes: int = 32) -> OpaqueToken:
    """Generate a URL-safe secret with a separate, non-secret correlation ID."""

    if entropy_bytes < 32:
        raise ValueError("opaque tokens require at least 32 bytes of entropy")
    token = secrets.token_urlsafe(entropy_bytes)
    return OpaqueToken(
        token_id=f"tok_{secrets.token_hex(8)}",
        token=token,
        token_hash=hash_opaque_token(token),
    )


def verify_opaque_token(candidate: str, expected_hash: str) -> bool:
    """Verify a supplied token without timing-sensitive string comparison."""

    if len(expected_hash) != 64:
        return False
    return hmac.compare_digest(hash_opaque_token(candidate), expected_hash.lower())


class BearerCredential(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["bearer"] = "bearer"
    token_id: str = Field(min_length=1)
    token: SecretStr

    def wire_value(self) -> dict[str, str]:
        return {
            "type": "bearer",
            "token_id": self.token_id,
            "token": self.token.get_secret_value(),
        }


class SourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(pattern=r"^https://")
    authorization: BearerCredential | None = None
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    media_type: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    page_number: int = Field(default=1, ge=1)


class ResultCallback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(pattern=r"^https://")
    authorization: BearerCredential


class ModalJobPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    parser: Literal["docling", "paddleocr", "paddleocr-vl", "mineru", "marker"]
    source: SourceReference
    result_callback: ResultCallback
    timeout_seconds: int = Field(default=900, ge=1, le=3600)

    def to_wire_dict(self) -> dict[str, Any]:
        """Serialize secrets only for the immediate authenticated wire request."""

        value = self.model_dump(mode="json")
        value["source"]["authorization"] = (
            self.source.authorization.wire_value()
            if self.source.authorization is not None
            else None
        )
        value["result_callback"]["authorization"] = (
            self.result_callback.authorization.wire_value()
        )
        return value


class ModalDispatchReceipt(BaseModel):
    model_config = ConfigDict(extra="ignore")

    call_id: str = Field(min_length=1)
    status: str = "accepted"


class ModalDispatchError(Exception):
    """A structured error safe for logs, persistence, and API responses."""

    def __init__(self, code: str, safe_message: str, *, retryable: bool) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message
        self.retryable = retryable


class ModalDispatcher:
    """Authenticated Modal HTTP dispatcher with bounded, safe failures."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        endpoint_key: str,
        endpoint_secret: str,
        timeout_seconds: float = 15,
        client: httpx.Client | None = None,
    ) -> None:
        if not endpoint_url.startswith("https://"):
            raise ValueError("Modal endpoint must use HTTPS")
        self._endpoint_url = endpoint_url
        self._endpoint_key = endpoint_key
        self._endpoint_secret = endpoint_secret
        self._timeout_seconds = timeout_seconds
        self._client = client

    def dispatch(self, payload: ModalJobPayload) -> ModalDispatchReceipt:
        headers = {
            "Modal-Key": self._endpoint_key,
            "Modal-Secret": self._endpoint_secret,
            "Content-Type": "application/json",
        }
        try:
            if self._client is None:
                response = httpx.post(
                    self._endpoint_url,
                    headers=headers,
                    json=payload.to_wire_dict(),
                    timeout=self._timeout_seconds,
                )
            else:
                response = self._client.post(
                    self._endpoint_url,
                    headers=headers,
                    json=payload.to_wire_dict(),
                    timeout=self._timeout_seconds,
                )
            response.raise_for_status()
            return ModalDispatchReceipt.model_validate(response.json())
        except httpx.TimeoutException as exc:
            raise ModalDispatchError(
                "modal_dispatch_timeout",
                "Modal did not accept the extraction job before the dispatch timeout",
                retryable=True,
            ) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise ModalDispatchError(
                "modal_dispatch_rejected",
                f"Modal rejected the extraction job (HTTP {status})",
                retryable=status in {408, 429, 500, 502, 503, 504},
            ) from exc
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ModalDispatchError(
                "modal_dispatch_failed",
                "Modal job dispatch failed or returned an invalid acknowledgement",
                retryable=isinstance(exc, httpx.HTTPError),
            ) from exc
