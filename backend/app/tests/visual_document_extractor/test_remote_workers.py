from __future__ import annotations

import io
import json
import uuid

import httpx
import pytest

from app.visual_document_extractor.execution import IsolatedExecutionError
from app.visual_document_extractor.models import PageClassification, PageInput
from app.visual_document_extractor.remote_workers import (
    _request_json,
    mistral_ocr_executor,
    openai_terra_executor,
)


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def _png_page() -> PageInput:
    from PIL import Image

    image = Image.new("RGB", (100, 50), "white")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return PageInput(
        document_id=uuid.uuid4(),
        page_number=1,
        media_type="image/png",
        content=output.getvalue(),
        classification=PageClassification.SCANNED,
    )


def test_mistral_normalizes_blocks_coordinates_and_page_confidence(
    monkeypatch,
) -> None:
    monkeypatch.setenv("MISTRAL_API_KEY", "test")
    monkeypatch.setattr(
        "app.visual_document_extractor.remote_workers.httpx.post",
        lambda *args, **kwargs: FakeResponse(
            {
                "model": "mistral-ocr-4-0",
                "pages": [
                    {
                        "index": 0,
                        "dimensions": {"width": 100, "height": 50},
                        "confidence_scores": {"average_page_confidence_score": 0.93},
                        "blocks": [
                            {
                                "type": "title",
                                "content": "Invoice",
                                "top_left_x": 5,
                                "top_left_y": 4,
                                "bottom_right_x": 90,
                                "bottom_right_y": 20,
                            }
                        ],
                    }
                ],
            }
        ),
    )

    result = mistral_ocr_executor(_png_page())

    assert result.attempt.confidence == 0.93
    assert result.elements[0].type == "heading"
    assert result.elements[0].bounding_box is not None
    assert result.elements[0].text == "Invoice"


def test_remote_provider_auth_failure_is_actionable_without_response_body(
    monkeypatch,
) -> None:
    request = httpx.Request("POST", "https://provider.invalid/ocr")
    response = httpx.Response(
        401,
        request=request,
        json={"message": "secret provider diagnostic"},
    )
    monkeypatch.setattr(
        "app.visual_document_extractor.remote_workers.httpx.post",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(IsolatedExecutionError) as caught:
        _request_json(
            "https://provider.invalid/ocr",
            api_key="test",
            payload={},
            timeout=1,
        )

    assert caught.value.code == "provider_auth_error"
    assert caught.value.safe_message.endswith("(HTTP 401)")
    assert "secret provider diagnostic" not in caught.value.safe_message


def test_openai_terra_uses_strict_schema_and_marks_output_model_derived(
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    captured: dict = {}

    def fake_post(*_args, **kwargs):
        captured.update(kwargs["json"])
        content = json.dumps(
            {
                "elements": [
                    {
                        "type": "paragraph",
                        "text": "Recovered page text",
                        "bounding_box": [10, 20, 900, 100],
                    }
                ]
            }
        )
        return FakeResponse(
            {"output": [{"content": [{"type": "output_text", "text": content}]}]}
        )

    monkeypatch.setattr(
        "app.visual_document_extractor.remote_workers.httpx.post", fake_post
    )

    result = openai_terra_executor(_png_page())

    assert captured["model"] == "gpt-5.6-terra"
    assert captured["text"]["format"]["strict"] is True
    assert result.attempt.model == "gpt-5.6-terra"
    assert result.elements[0].model_derived is True
    assert result.elements[0].confidence is None
