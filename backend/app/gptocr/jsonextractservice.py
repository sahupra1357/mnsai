import json
from typing import Any

from fastapi import HTTPException
from openai import OpenAI, OpenAIError

from app.core.config import settings
from app.gptocr.logger import logger
from app.gptocr.utilityFunction import retry_with_backoff

# ----------------------------
# JSON Extraction Service
# ----------------------------

_SYSTEM_PROMPT = """
You are a document data extraction specialist.

Given extracted text/markdown from a document, your job is to:
1. Identify the exact document type (e.g. invoice, bill, tax_invoice, purchase_order,
   utility_bill, passport, driving_license, aadhaar_card, voter_id, green_card,
   birth_certificate, contract, receipt, bank_statement, medical_report, etc.)
2. Extract EVERY piece of information from the text and organise it into a
   well-structured, hierarchical JSON object.

## Completeness rules — CRITICAL
- **Include every field visible in the source text. Do not skip, summarise, or
  merge any fields, no matter how many there are.**
- For line-item tables: output EVERY row as a separate object in the array.
  If there are 50 line items, output all 50. Never truncate or say "... and more".
- For multi-page documents: capture fields from ALL pages.
- If a field label exists in the source but the value is blank/illegible, represent
  it as an empty string "" rather than omitting it — so the consumer knows the field
  exists.
- Do NOT invent or infer values that are not explicitly present in the source text.

## Format rules
- Return ONLY valid JSON — no markdown fences, no explanation, no trailing text.
- The root object MUST have exactly two keys:
    "document_type" : a short snake_case string identifying the document
    "data"          : an object containing all extracted fields, nested appropriately

- Structure the "data" object dynamically based on the document type:
  - For invoices / bills group fields under logical parents such as:
      vendor, buyer, invoice_details, line_items (array), totals, payment_terms,
      bank_details, additional_charges, notes
  - For identity documents group fields such as:
      personal_info, document_info, address, additional_fields
  - For contracts group fields such as:
      parties, terms, dates, signatures, clauses
  - For any other type use the most logical grouping; add extra sub-objects
    as needed to capture every field present.

- Use snake_case for every key.
- Preserve all numeric values as numbers (not strings) where possible.
- Preserve dates in ISO-8601 format (YYYY-MM-DD) where unambiguous; otherwise keep
  the original string.
- For tabular/line-item data always use a JSON array of objects.

## Output shape example (invoice)
{
  "document_type": "invoice",
  "data": {
    "vendor": {
      "name": "Acme Corp",
      "address": "123 Main St, City",
      "gstin": "29ABCDE1234F1Z5",
      "contact": "+91-9876543210"
    },
    "buyer": {
      "name": "XYZ Ltd",
      "address": "456 Park Ave, Town"
    },
    "invoice_details": {
      "invoice_number": "INV-2024-001",
      "invoice_date": "2024-01-15",
      "due_date": "2024-02-15",
      "ref_no": "REF123",
      "ref_date": "2024-01-10"
    },
    "line_items": [
      {
        "description": "Widget A",
        "hsn_sac": "8471",
        "quantity": 10,
        "unit_price": 500.00,
        "total_price": 5000.00
      }
    ],
    "totals": {
      "subtotal": 5000.00,
      "tax": 900.00,
      "grand_total": 5900.00,
      "currency": "INR"
    },
    "payment_terms": "Net 30"
  }
}
"""


class JsonExtractService:
    def __init__(self):
        try:
            self.client = OpenAI()
        except Exception as e:
            logger.exception(f"Failed to initialize OpenAI client for JSON extraction: {e}")
            raise RuntimeError(f"Failed to initialize OpenAI client: {e}")

    async def extract_json(self, extracted_text: str) -> dict[str, Any]:
        """
        Convert raw OCR-extracted markdown text into a hierarchical JSON document.

        Args:
            extracted_text: The markdown text returned by the OCR step.

        Returns:
            dict with keys ``document_type`` (str) and ``data`` (dict).
        """
        async def _request():
            try:
                response = self.client.chat.completions.create(
                    model=settings.OPENAI_DEPLOYMENT_ID,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": (
                                "Extract EVERY field from the document below into JSON. "
                                "Do not skip any line items or fields.\n\n"
                                + extracted_text
                            ),
                        },
                    ],
                    temperature=0.0,
                    max_tokens=16000,
                )
                choice = response.choices[0]
                if choice.finish_reason == "length":
                    logger.warning(
                        "JSON extraction hit max_tokens limit — output may be truncated. "
                        f"Input text length: {len(extracted_text)} chars."
                    )
                raw = choice.message.content.strip()
                logger.info(f"JSON extraction response length: {len(raw)} chars.")
                return self._parse_response(raw)
            except OpenAIError as e:
                if "rate limit" in str(e).lower():
                    raise HTTPException(status_code=429, detail="Rate limit exceeded.")
                logger.error(f"OpenAI API error during JSON extraction: {e}")
                raise HTTPException(status_code=502, detail=f"JSON extraction failed: {e}")
            except HTTPException:
                raise
            except Exception as e:
                logger.exception(f"Unexpected error during JSON extraction: {e}")
                raise HTTPException(status_code=500, detail=f"JSON extraction failed: {e}")

        return await retry_with_backoff(_request)

    def _parse_response(self, raw: str) -> dict[str, Any]:
        """Parse the raw JSON string and validate the expected envelope."""
        try:
            result = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}. Raw response: {raw[:500]}")
            raise HTTPException(
                status_code=500,
                detail="JSON extraction returned an invalid JSON response.",
            )

        if not isinstance(result, dict):
            raise HTTPException(
                status_code=500,
                detail="JSON extraction response is not an object.",
            )

        # Normalise: ensure required top-level keys exist
        if "document_type" not in result:
            result["document_type"] = "unknown"
        if "data" not in result:
            # If model returned flat keys, promote everything except document_type into data
            doc_type = result.pop("document_type", "unknown")
            result = {"document_type": doc_type, "data": result}

        return result


# Singleton
json_extract_service = JsonExtractService()
