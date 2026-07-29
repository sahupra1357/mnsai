from __future__ import annotations

import pytest

from app.visual_document_extractor.classification import (
    ClassificationConfig,
    PageEvidence,
    ParserRoute,
    classify_document,
    classify_page,
    measure_page_signals,
)
from app.visual_document_extractor.models import PageClassification

PDF = "application/pdf"
PNG = "image/png"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_routes_usable_native_pdf_to_docling_with_measurements() -> None:
    evidence = PageEvidence(
        page_number=1,
        media_type=PDF,
        native_text=(
            "This digitally authored quarterly report contains readable native "
            "text in a consistent reading order."
        ),
        page_area=1000,
        native_text_area=300,
        raster_area=20,
        native_text_blocks=3,
        layout_regions=3,
    )

    decision = classify_page(evidence)

    assert decision.classification == PageClassification.DIGITAL
    assert decision.recommended_parser == ParserRoute.DOCLING
    assert decision.signals.native_text_characters >= 40
    assert decision.signals.raster_coverage == pytest.approx(0.02)
    assert any(
        "usable native text layer" in reason for reason in decision.routing_reasons
    )


def test_routes_native_docx_to_docling() -> None:
    decision = classify_page(
        PageEvidence(
            page_number=1,
            media_type=DOCX,
            native_text="A sufficiently long and plausible native paragraph " * 2,
        )
    )

    assert decision.classification == PageClassification.DIGITAL
    assert decision.recommended_parser == ParserRoute.DOCLING


def test_office_package_keeps_native_docling_route_without_preview_text() -> None:
    decision = classify_page(PageEvidence(page_number=1, media_type=DOCX))

    assert decision.classification == PageClassification.DIGITAL
    assert decision.recommended_parser == ParserRoute.DOCLING
    assert any("native Office package" in reason for reason in decision.routing_reasons)


def test_routes_raster_image_to_paddleocr() -> None:
    decision = classify_page(
        PageEvidence(
            page_number=1,
            media_type=PNG,
            page_area=1000,
            raster_area=1000,
            layout_regions=2,
        )
    )

    assert decision.classification == PageClassification.SCANNED
    assert decision.recommended_parser == ParserRoute.PADDLEOCR
    assert decision.signals.raster_coverage == 1
    assert any(
        "scanned-page threshold" in reason for reason in decision.routing_reasons
    )


def test_routes_complex_scanned_layout_to_paddleocr_vl() -> None:
    decision = classify_page(
        PageEvidence(
            page_number=2,
            media_type=PDF,
            page_area=1000,
            raster_area=950,
            layout_regions=18,
            column_count=3,
            table_count=2,
            reading_order_consistent=False,
        )
    )

    assert decision.classification == PageClassification.COMPLEX_LAYOUT
    assert decision.recommended_parser == ParserRoute.PADDLEOCR_VL
    assert decision.signals.complex_layout_score >= 0.55


def test_routes_formula_scientific_page_to_mineru() -> None:
    decision = classify_page(
        PageEvidence(
            page_number=3,
            media_type=PDF,
            native_text=(
                "Abstract theorem proof experiment methodology references "
                "The result is ∫ f(x) dx = α ± β and $\\frac{a}{b}$."
            ),
            page_area=1000,
            formula_count=3,
            column_count=2,
        )
    )

    assert decision.classification == PageClassification.FORMULA_HEAVY
    assert decision.recommended_parser == ParserRoute.MINERU
    assert decision.signals.formula_score >= 0.45
    assert decision.signals.scientific_score >= 0.50


def test_bad_native_text_is_not_treated_as_digital() -> None:
    decision = classify_page(
        PageEvidence(
            page_number=1,
            media_type=PDF,
            native_text="\ufffd" * 60,
            page_area=1000,
            raster_area=900,
        )
    )

    assert decision.classification == PageClassification.SCANNED
    assert decision.recommended_parser == ParserRoute.PADDLEOCR
    assert decision.signals.replacement_character_ratio == 1


def test_unknown_when_native_and_raster_evidence_are_insufficient() -> None:
    decision = classify_page(
        PageEvidence(page_number=1, media_type=PDF, native_text="tiny")
    )

    assert decision.classification == PageClassification.UNKNOWN
    assert "insufficient" in decision.routing_reasons[-1]


def test_mixed_document_routes_pages_independently_and_in_order() -> None:
    result = classify_document(
        [
            PageEvidence(
                page_number=2,
                media_type=PDF,
                page_area=1000,
                raster_area=950,
            ),
            PageEvidence(
                page_number=1,
                media_type=PDF,
                native_text="A plausible digital page with sufficient native text. "
                * 2,
            ),
        ]
    )

    assert result.mixed is True
    assert result.classification == "mixed"
    assert [page.page_number for page in result.page_decisions] == [1, 2]
    assert [page.recommended_parser for page in result.page_decisions] == [
        ParserRoute.DOCLING,
        ParserRoute.PADDLEOCR,
    ]


def test_operator_override_is_validated_and_recorded() -> None:
    evidence = PageEvidence(
        page_number=1,
        media_type=PDF,
        native_text="A plausible digital page with sufficient native text. " * 2,
    )

    decision = classify_page(evidence, operator_parser=ParserRoute.MINERU)

    assert decision.recommended_parser == ParserRoute.MINERU
    assert decision.operator_override is True
    assert decision.routing_reasons[-1] == "operator override selected parser=mineru"

    with pytest.raises(ValueError, match="Unsupported parser override"):
        classify_page(evidence, operator_parser="not-a-parser")


def test_thresholds_are_configurable() -> None:
    evidence = PageEvidence(
        page_number=1,
        media_type=PDF,
        native_text="Short but plausible",
    )

    default_decision = classify_page(evidence)
    configured_decision = classify_page(
        evidence,
        config=ClassificationConfig(min_native_text_characters=10),
    )

    assert default_decision.classification == PageClassification.UNKNOWN
    assert configured_decision.classification == PageClassification.DIGITAL


def test_measurements_do_not_fabricate_unavailable_density_or_coverage() -> None:
    measured = measure_page_signals(
        PageEvidence(
            page_number=1,
            media_type=PDF,
            native_text="Readable content",
        )
    )

    assert measured.stored.native_text_density is None
    assert measured.stored.raster_coverage is None
    assert "raster_coverage=null" in measured.stored.reasons


def test_rejects_duplicate_pages_and_unknown_override_pages() -> None:
    page = PageEvidence(page_number=1, media_type=PNG)

    with pytest.raises(ValueError, match="unique"):
        classify_document([page, page])
    with pytest.raises(ValueError, match=r"unknown page\(s\): 2"):
        classify_document([page], operator_parsers={2: ParserRoute.PADDLEOCR})
