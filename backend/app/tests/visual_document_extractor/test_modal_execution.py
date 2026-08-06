from __future__ import annotations

import json

import httpx
import pytest

from app.visual_document_extractor.modal_execution import (
    BearerCredential,
    ModalDispatcher,
    ModalDispatchError,
    ModalJobPayload,
    ResultCallback,
    SourceReference,
    generate_opaque_token,
    verify_opaque_token,
)


def _payload(
    source_token: str = "source-secret", result_token: str = "result-secret"
) -> ModalJobPayload:
    return ModalJobPayload(
        job_id="job-1",
        document_id="doc-1",
        attempt_id="attempt-1",
        parser="docling",
        source=SourceReference(
            url="https://api.example.test/modal/jobs/job-1/source",
            authorization=BearerCredential(token_id="tok_source", token=source_token),
            sha256="a" * 64,
            media_type="application/pdf",
            source_name="sample.pdf",
        ),
        result_callback=ResultCallback(
            url="https://api.example.test/modal/jobs/job-1/result",
            authorization=BearerCredential(token_id="tok_result", token=result_token),
        ),
    )


def test_opaque_token_is_verifiable_and_repr_is_redacted() -> None:
    material = generate_opaque_token()

    assert material.token_id.startswith("tok_")
    assert verify_opaque_token(material.token, material.token_hash)
    assert not verify_opaque_token(material.token + "x", material.token_hash)
    assert material.token not in repr(material)


def test_payload_repr_redacts_both_tokens_but_wire_payload_contains_them() -> None:
    payload = _payload()

    assert "source-secret" not in repr(payload)
    assert "result-secret" not in repr(payload)
    wire = payload.to_wire_dict()
    assert wire["source"]["authorization"]["token"] == "source-secret"
    assert wire["result_callback"]["authorization"]["token"] == "result-secret"


def test_modal_image_schema_accepts_exact_wire_payload() -> None:
    payload = _payload()

    parsed = ModalJobPayload.model_validate(payload.to_wire_dict())

    assert parsed.source.authorization is not None
    assert parsed.source.authorization.type == "bearer"
    assert parsed.result_callback.authorization.type == "bearer"


def test_dispatch_uses_separate_endpoint_auth_and_returns_receipt() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = request.headers
        seen["body"] = json.loads(request.content)
        return httpx.Response(202, json={"call_id": "fc-123", "status": "accepted"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        dispatcher = ModalDispatcher(
            endpoint_url="https://modal.example.test/submit",
            endpoint_key="endpoint-key",
            endpoint_secret="endpoint-secret",
            client=client,
        )
        receipt = dispatcher.dispatch(_payload())

    assert receipt.call_id == "fc-123"
    headers = seen["headers"]
    assert isinstance(headers, httpx.Headers)
    assert headers["Modal-Key"] == "endpoint-key"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["source"]["authorization"]["token"] == "source-secret"


def test_dispatch_failure_is_safe_and_does_not_expose_tokens() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "source-secret result-secret"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        dispatcher = ModalDispatcher(
            endpoint_url="https://modal.example.test/submit",
            endpoint_key="endpoint-key",
            endpoint_secret="endpoint-secret",
            client=client,
        )
        with pytest.raises(ModalDispatchError) as caught:
            dispatcher.dispatch(_payload())

    message = str(caught.value)
    assert "source-secret" not in message
    assert "result-secret" not in message
    assert caught.value.code == "modal_dispatch_rejected"
    assert not caught.value.retryable


def test_dispatch_requires_https() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        ModalDispatcher(
            endpoint_url="http://modal.example.test/submit",
            endpoint_key="key",
            endpoint_secret="secret",
        )
