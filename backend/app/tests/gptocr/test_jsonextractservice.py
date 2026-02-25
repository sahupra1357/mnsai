"""
Unit tests for JsonExtractService.

Covers:
  - _parse_response: all branches (valid, missing keys, bad JSON, non-object)
  - extract_json: happy-path with the OpenAI client fully mocked
"""
import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.gptocr.jsonextractservice import JsonExtractService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_service() -> JsonExtractService:
    """Return a JsonExtractService whose OpenAI client is a MagicMock."""
    with patch("app.gptocr.jsonextractservice.OpenAI"):
        svc = JsonExtractService()
    svc.client = MagicMock()
    return svc


def _fake_openai_response(content: str):
    """Build a minimal object that mimics an OpenAI chat completion response."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


# ===========================================================================
# _parse_response tests  (synchronous – no asyncio required)
# ===========================================================================

class TestParseResponse:

    def test_valid_envelope_returned_unchanged(self):
        svc = make_service()
        payload = {"document_type": "invoice", "data": {"vendor": {"name": "Acme"}}}
        result = svc._parse_response(json.dumps(payload))
        assert result["document_type"] == "invoice"
        assert result["data"]["vendor"]["name"] == "Acme"

    def test_missing_document_type_defaults_to_unknown(self):
        svc = make_service()
        payload = {"data": {"invoice_number": "INV-001"}}
        result = svc._parse_response(json.dumps(payload))
        assert result["document_type"] == "unknown"
        assert result["data"]["invoice_number"] == "INV-001"

    def test_flat_keys_promoted_into_data_when_data_missing(self):
        """If GPT returns a flat object without a 'data' wrapper, promote it."""
        svc = make_service()
        payload = {"document_type": "passport", "name": "John Doe", "number": "A1234567"}
        result = svc._parse_response(json.dumps(payload))
        assert result["document_type"] == "passport"
        # All non-document_type keys end up under 'data'
        assert result["data"]["name"] == "John Doe"
        assert result["data"]["number"] == "A1234567"

    def test_invalid_json_raises_http_500(self):
        svc = make_service()
        with pytest.raises(HTTPException) as exc_info:
            svc._parse_response("this is not json at all")
        assert exc_info.value.status_code == 500
        assert "invalid json" in exc_info.value.detail.lower()

    def test_json_array_at_root_raises_http_500(self):
        svc = make_service()
        with pytest.raises(HTTPException) as exc_info:
            svc._parse_response(json.dumps([{"document_type": "invoice"}]))
        assert exc_info.value.status_code == 500
        assert "not an object" in exc_info.value.detail.lower()

    def test_nested_line_items_preserved(self):
        svc = make_service()
        payload = {
            "document_type": "invoice",
            "data": {
                "line_items": [
                    {"description": "Widget", "quantity": 5, "unit_price": 100.0}
                ],
                "totals": {"grand_total": 500.0, "currency": "INR"},
            },
        }
        result = svc._parse_response(json.dumps(payload))
        items = result["data"]["line_items"]
        assert len(items) == 1
        assert items[0]["quantity"] == 5
        assert result["data"]["totals"]["grand_total"] == 500.0


# ===========================================================================
# extract_json tests  (async – run with asyncio.run)
# ===========================================================================

class TestExtractJson:

    def test_happy_path_invoice(self):
        svc = make_service()

        expected = {
            "document_type": "invoice",
            "data": {
                "vendor": {"name": "Acme Corp"},
                "invoice_details": {"invoice_number": "INV-001"},
                "totals": {"grand_total": 5000.0, "currency": "USD"},
            },
        }
        svc.client.chat.completions.create.return_value = _fake_openai_response(
            json.dumps(expected)
        )

        result = asyncio.run(svc.extract_json("## Invoice\nVendor: Acme Corp\nTotal: $5000"))

        assert result["document_type"] == "invoice"
        assert result["data"]["vendor"]["name"] == "Acme Corp"
        assert result["data"]["totals"]["grand_total"] == 5000.0

    def test_happy_path_passport(self):
        svc = make_service()

        expected = {
            "document_type": "passport",
            "data": {
                "personal_info": {"name": "Jane Smith", "nationality": "US"},
                "document_info": {"passport_number": "X9876543", "expiry_date": "2030-05-01"},
            },
        }
        svc.client.chat.completions.create.return_value = _fake_openai_response(
            json.dumps(expected)
        )

        result = asyncio.run(svc.extract_json("Passport extracted text..."))

        assert result["document_type"] == "passport"
        assert result["data"]["personal_info"]["name"] == "Jane Smith"

    def test_openai_rate_limit_raises_http_429(self):
        """A rate-limit OpenAI error should surface as HTTP 429.

        We replace retry_with_backoff with a single-shot version so the test
        doesn't sleep through real exponential backoff delays.
        """
        from openai import OpenAIError

        async def _no_retry(func, *_args, **_kwargs):
            return await func()

        svc = make_service()
        svc.client.chat.completions.create.side_effect = OpenAIError("rate limit exceeded")

        with patch("app.gptocr.jsonextractservice.retry_with_backoff", new=_no_retry):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(svc.extract_json("some text"))
        assert exc_info.value.status_code == 429

    def test_openai_generic_error_raises_http_502(self):
        """A non-rate-limit OpenAI error should surface as HTTP 502 immediately."""
        from openai import OpenAIError

        async def _no_retry(func, *_args, **_kwargs):
            return await func()

        svc = make_service()
        svc.client.chat.completions.create.side_effect = OpenAIError("connection error")

        with patch("app.gptocr.jsonextractservice.retry_with_backoff", new=_no_retry):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(svc.extract_json("some text"))
        assert exc_info.value.status_code == 502

    def test_openai_json_response_format_is_requested(self):
        """Verify the call includes response_format=json_object."""
        svc = make_service()

        expected = {"document_type": "bill", "data": {"amount": 99.9}}
        svc.client.chat.completions.create.return_value = _fake_openai_response(
            json.dumps(expected)
        )

        asyncio.run(svc.extract_json("Bill text"))

        call_kwargs = svc.client.chat.completions.create.call_args.kwargs
        assert call_kwargs.get("response_format") == {"type": "json_object"}
        assert call_kwargs.get("temperature") == 0.0
