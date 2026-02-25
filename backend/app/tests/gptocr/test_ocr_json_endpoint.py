"""
Integration tests for POST /api/v1/gptfiles/ocr-json.

All external calls (OpenAI, PDF conversion, DB) are mocked so no live
services are required.
"""
import io
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# conftest.py supplies the `client` fixture with auth + DB overridden.

ENDPOINT = "/api/v1/gptfiles/ocr-json"

# Minimal valid PNG header bytes (1×1 white pixel) – avoids real PDF parsing.
_FAKE_IMAGE_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
    b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
    b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)

_INVOICE_JSON = {
    "document_type": "invoice",
    "data": {
        "vendor": {"name": "Acme Corp", "gstin": "29ABCDE1234F1Z5"},
        "invoice_details": {"invoice_number": "INV-2024-001", "invoice_date": "2024-01-15"},
        "line_items": [
            {"description": "Widget A", "quantity": 10, "unit_price": 500.0, "total_price": 5000.0}
        ],
        "totals": {"subtotal": 5000.0, "tax": 900.0, "grand_total": 5900.0, "currency": "INR"},
    },
}

_PASSPORT_JSON = {
    "document_type": "passport",
    "data": {
        "personal_info": {"name": "Jane Smith", "date_of_birth": "1990-04-12"},
        "document_info": {"passport_number": "X9876543", "expiry_date": "2030-05-01"},
    },
}


def _upload_file(content: bytes = _FAKE_IMAGE_BYTES, filename: str = "doc.pdf",
                 content_type: str = "application/pdf"):
    """Return a files dict for multipart upload."""
    return {"file": (filename, io.BytesIO(content), content_type)}


def _all_mocks(extr_count: int = 0, extracted_text: str = "extracted text",
               json_result: dict = None):
    """
    Context-manager stack that patches every external dependency of the
    /ocr-json endpoint.
    """
    if json_result is None:
        json_result = _INVOICE_JSON

    patches = [
        patch(
            "app.api.routes.extractorgpt.read_extr_count",
            return_value=extr_count,
        ),
        patch("app.api.routes.extractorgpt.create_extr"),
        patch(
            "app.api.routes.extractorgpt.get_pdf_bytes",
            new_callable=AsyncMock,
            return_value=_FAKE_IMAGE_BYTES,
        ),
        patch(
            "app.api.routes.extractorgpt.convert_pdf_to_images_pymupdf",
            return_value=[(1, _FAKE_IMAGE_BYTES)],
        ),
        patch(
            "app.api.routes.extractorgpt.process_batches",
            new_callable=AsyncMock,
            return_value=[extracted_text],
        ),
        patch(
            "app.api.routes.extractorgpt.concatenate_texts",
            return_value=extracted_text,
        ),
        patch.object(
            # Patch the singleton's method directly
            __import__(
                "app.gptocr.jsonextractservice",
                fromlist=["json_extract_service"],
            ).json_extract_service,
            "extract_json",
            new_callable=AsyncMock,
            return_value=json_result,
        ),
    ]
    return patches


class TestOcrJsonEndpoint:

    # ------------------------------------------------------------------
    # Happy path – invoice document
    # ------------------------------------------------------------------
    def test_invoice_returns_200_with_correct_shape(self, client):
        patches = _all_mocks(json_result=_INVOICE_JSON)
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
        ):
            resp = client.post(ENDPOINT, files=_upload_file())

        assert resp.status_code == 200
        body = resp.json()
        assert body["document_type"] == "invoice"
        assert "vendor" in body["data"]
        assert body["data"]["vendor"]["name"] == "Acme Corp"
        assert "line_items" in body["data"]
        assert isinstance(body["data"]["line_items"], list)
        assert body["data"]["totals"]["grand_total"] == 5900.0

    # ------------------------------------------------------------------
    # Happy path – passport document
    # ------------------------------------------------------------------
    def test_passport_returns_200_with_correct_shape(self, client):
        patches = _all_mocks(json_result=_PASSPORT_JSON)
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
        ):
            resp = client.post(ENDPOINT, files=_upload_file())

        assert resp.status_code == 200
        body = resp.json()
        assert body["document_type"] == "passport"
        assert body["data"]["personal_info"]["name"] == "Jane Smith"
        assert body["data"]["document_info"]["passport_number"] == "X9876543"

    # ------------------------------------------------------------------
    # Quota exceeded → 403
    # ------------------------------------------------------------------
    def test_extraction_limit_exceeded_returns_403(self, client):
        # Set count above MAX_EXTR_COUNT (default 70; pass a huge number)
        patches = _all_mocks(extr_count=9999)
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
        ):
            resp = client.post(ENDPOINT, files=_upload_file())

        assert resp.status_code == 403
        assert "Maximum number of extractions" in resp.json()["detail"]

    # ------------------------------------------------------------------
    # Invalid file type → 400
    # ------------------------------------------------------------------
    def test_invalid_file_type_returns_400(self, client):
        """Uploading a .txt file should be rejected before OCR starts."""
        with patch("app.api.routes.extractorgpt.read_extr_count", return_value=0):
            resp = client.post(
                ENDPOINT,
                files=_upload_file(content=b"not a pdf", filename="doc.txt", content_type="text/plain"),
            )
        assert resp.status_code == 400

    # ------------------------------------------------------------------
    # JSON extraction failure propagated correctly
    # ------------------------------------------------------------------
    def test_json_extraction_failure_returns_500(self, client):
        from fastapi import HTTPException as FastHTTP

        async def _fail(_text):
            raise FastHTTP(status_code=500, detail="JSON extraction failed: mock error")

        patches = _all_mocks()
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
        ):
            singleton = __import__(
                "app.gptocr.jsonextractservice",
                fromlist=["json_extract_service"],
            ).json_extract_service

            with patch.object(singleton, "extract_json", side_effect=_fail):
                resp = client.post(ENDPOINT, files=_upload_file())

        assert resp.status_code == 500

    # ------------------------------------------------------------------
    # Response schema validation
    # ------------------------------------------------------------------
    def test_response_always_has_document_type_and_data_keys(self, client):
        patches = _all_mocks(json_result={"document_type": "unknown", "data": {"raw": "..."}})
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
        ):
            resp = client.post(ENDPOINT, files=_upload_file())

        assert resp.status_code == 200
        body = resp.json()
        assert "document_type" in body
        assert "data" in body
        assert isinstance(body["data"], dict)
