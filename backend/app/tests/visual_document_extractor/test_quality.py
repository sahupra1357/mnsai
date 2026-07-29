from __future__ import annotations

import uuid

from app.visual_document_extractor.models import (
    AdapterResult,
    AttemptStatus,
    BoundingBox,
    CoordinateSpace,
    ExtractedElement,
    ExtractionAttempt,
    PageClassification,
    PageInput,
)
from app.visual_document_extractor.quality import (
    QualityPolicy,
    choose_best_candidate,
    validate_result,
)


def _page(classification: PageClassification = PageClassification.DIGITAL) -> PageInput:
    return PageInput(
        document_id=uuid.uuid4(),
        page_number=1,
        media_type="application/pdf",
        content=b"page",
        classification=classification,
        coordinate_space=CoordinateSpace(width=100, height=200),
    )


def _result(
    text: str = "A useful extracted sentence.",
    *,
    confidence: float | None = 0.9,
    element_type: str = "paragraph",
    bbox: BoundingBox | None = None,
) -> AdapterResult:
    return AdapterResult(
        attempt=ExtractionAttempt(
            parser="test",
            version="1",
            status=AttemptStatus.SUCCEEDED,
            confidence=confidence,
        ),
        elements=[
            ExtractedElement(
                element_id="e1",
                type=element_type,
                text=text,
                reading_order=0,
                bounding_box=bbox,
                coordinate_space=CoordinateSpace(width=100, height=200)
                if bbox
                else None,
                confidence=confidence,
                confidence_source="parser" if confidence is not None else None,
            )
        ],
    )


def test_quality_accepts_plausible_output_without_fabricating_confidence() -> None:
    result = _result(confidence=None)
    assessment = validate_result(_page(), result)

    assert assessment.passed is True
    assert result.attempt.confidence is None
    confidence_signal = next(
        signal for signal in assessment.signals if signal.name == "confidence"
    )
    assert confidence_signal.passed is None


def test_quality_rejects_empty_text_and_out_of_bounds_coordinates() -> None:
    result = _result(
        text="",
        bbox=BoundingBox(left=0, top=0, right=101, bottom=40),
    )
    assessment = validate_result(_page(), result)

    assert assessment.passed is False
    assert {"minimum_text", "coordinates"}.issubset(assessment.failed_checks)


def test_formula_page_requires_formula_element() -> None:
    assessment = validate_result(
        _page(PageClassification.FORMULA_HEAVY),
        _result("The equation was omitted."),
    )

    assert assessment.passed is False
    assert "formula_presence" in assessment.failed_checks


def test_duplicate_reading_order_is_rejected() -> None:
    result = _result()
    result.elements.append(
        ExtractedElement(
            element_id="e2",
            text="Second block",
            reading_order=0,
        )
    )

    assessment = validate_result(_page(), result)

    assert assessment.passed is False
    assert "reading_order" in assessment.failed_checks


def test_candidate_comparison_prefers_valid_output_over_provider_confidence() -> None:
    invalid_high_confidence = _result("", confidence=0.99)
    valid_lower_confidence = _result("Useful complete output", confidence=0.7)

    selected = choose_best_candidate(
        _page(),
        [invalid_high_confidence, valid_lower_confidence],
        QualityPolicy(minimum_confidence=0.5),
    )

    assert selected is valid_lower_confidence
