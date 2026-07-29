from __future__ import annotations

import io
import shutil
import uuid

import pytest

from app.visual_document_extractor.adapters import SecondaryOCRAdapter
from app.visual_document_extractor.models import (
    AttemptStatus,
    PageClassification,
    PageInput,
)


@pytest.mark.skipif(
    shutil.which("tesseract") is None,
    reason="Tesseract binary is not installed",
)
def test_real_tesseract_extracts_text_and_coordinates() -> None:
    pillow = pytest.importorskip("PIL.Image")
    image_draw = pytest.importorskip("PIL.ImageDraw")
    image = pillow.new("RGB", (900, 220), "white")
    draw = image_draw.Draw(image)
    draw.text((35, 60), "VISUAL EXTRACTION 7429", fill="black", font_size=52)
    payload = io.BytesIO()
    image.save(payload, format="PNG")
    page = PageInput(
        document_id=uuid.uuid4(),
        page_number=1,
        media_type="image/png",
        content=payload.getvalue(),
        classification=PageClassification.SCANNED,
        timeout_seconds=15,
    )

    adapter = SecondaryOCRAdapter()
    result = adapter.extract(page)

    assert adapter.probe().available is True
    assert result.attempt.status is AttemptStatus.SUCCEEDED
    assert "7429" in " ".join(element.text for element in result.elements)
    assert all(element.bounding_box is not None for element in result.elements)
    assert all(element.coordinate_space is not None for element in result.elements)
    assert all(
        element.source_block_number is not None
        and element.source_paragraph_number is not None
        and element.source_line_number is not None
        and element.source_word_number is not None
        for element in result.elements
    )


def test_missing_tesseract_is_reported_as_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.visual_document_extractor.adapters.parsers.tesseract_available",
        lambda: False,
    )
    adapter = SecondaryOCRAdapter()

    capability = adapter.probe()

    assert capability.available is False
    assert "not configured" in (capability.reason or "")
