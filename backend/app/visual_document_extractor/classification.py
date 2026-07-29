"""Measurable page classification and initial parser recommendations."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum

from .models import ClassificationSignals, PageClassification


class ParserRoute(str, Enum):
    DOCLING = "docling"
    PADDLEOCR = "paddleocr"
    PADDLEOCR_VL = "paddleocr-vl"
    MINERU = "mineru"


@dataclass(frozen=True, slots=True)
class ClassificationConfig:
    min_native_text_characters: int = 40
    min_native_alnum_ratio: float = 0.55
    max_replacement_character_ratio: float = 0.02
    scanned_raster_coverage: float = 0.60
    formula_score_threshold: float = 0.45
    scientific_score_threshold: float = 0.50
    complex_layout_score_threshold: float = 0.55
    paddleocr_vl_score_threshold: float = 0.55
    dense_layout_regions: int = 12

    def __post_init__(self) -> None:
        if self.min_native_text_characters < 1:
            raise ValueError("min_native_text_characters must be positive")
        if self.dense_layout_regions < 1:
            raise ValueError("dense_layout_regions must be positive")
        for name in (
            "min_native_alnum_ratio",
            "max_replacement_character_ratio",
            "scanned_raster_coverage",
            "formula_score_threshold",
            "scientific_score_threshold",
            "complex_layout_score_threshold",
            "paddleocr_vl_score_threshold",
        ):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class PageEvidence:
    """Parser-independent observations collected while inspecting one page."""

    page_number: int
    media_type: str
    native_text: str = ""
    page_area: float | None = None
    native_text_area: float | None = None
    raster_area: float | None = None
    native_text_blocks: int = 0
    layout_regions: int = 0
    column_count: int = 1
    table_count: int = 0
    formula_count: int = 0
    reading_order_consistent: bool = True
    rotation_degrees: int = 0

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("page_number must be at least 1")
        if not self.media_type:
            raise ValueError("media_type is required")
        for name in (
            "native_text_blocks",
            "layout_regions",
            "table_count",
            "formula_count",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative")
        if self.column_count < 1:
            raise ValueError("column_count must be at least 1")
        for name in ("page_area", "native_text_area", "raster_area"):
            value = getattr(self, name)
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ValueError(f"{name} must be a finite non-negative number")
        if (
            self.page_area is not None
            and self.page_area == 0
            and (self.native_text_area or self.raster_area)
        ):
            raise ValueError("page_area must be positive when coverage areas are set")


@dataclass(frozen=True, slots=True)
class MeasuredPageSignals:
    stored: ClassificationSignals
    native_alnum_ratio: float | None
    math_symbol_ratio: float
    scientific_keyword_count: int
    usable_native_text: bool
    reading_order_consistent: bool
    table_count: int
    column_count: int
    layout_regions: int


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    page_number: int
    classification: PageClassification
    recommended_parser: ParserRoute
    signals: ClassificationSignals
    routing_reasons: tuple[str, ...]
    operator_override: bool = False


@dataclass(frozen=True, slots=True)
class DocumentClassification:
    classification: str
    page_decisions: tuple[RoutingDecision, ...]
    mixed: bool
    routing_reasons: tuple[str, ...] = field(default_factory=tuple)


_IMAGE_MEDIA_TYPES = {
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/bmp",
    "image/gif",
    "image/webp",
}
_OFFICE_MEDIA_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
_NATIVE_DOCUMENT_MEDIA_TYPES = {"application/pdf", *_OFFICE_MEDIA_TYPES}
_SCIENTIFIC_TERMS = re.compile(
    r"\b(?:abstract|algorithm|appendix|corollary|dataset|equation|experiment|"
    r"hypothesis|lemma|methodology|proof|references|theorem)\b",
    re.IGNORECASE,
)
_MATH_SYMBOLS = frozenset("=±×÷∑∫√∞≈≠≤≥∂∆∇∏∈∉⊂⊆∪∩→←↔αβγδθλμσφψω")
_LATEX_TOKENS = re.compile(
    r"(?:\\(?:frac|sum|int|sqrt|begin|end|alpha|beta|theta|lambda)\b|"
    r"\$[^$\n]{1,200}\$)"
)


def measure_page_signals(
    evidence: PageEvidence,
    *,
    config: ClassificationConfig | None = None,
) -> MeasuredPageSignals:
    active_config = config or ClassificationConfig()
    text = evidence.native_text or ""
    native_characters = len(text.strip())
    non_space_characters = [character for character in text if not character.isspace()]
    alnum_characters = sum(character.isalnum() for character in non_space_characters)
    native_alnum_ratio = (
        alnum_characters / len(non_space_characters) if non_space_characters else None
    )
    replacement_ratio = (
        text.count("\ufffd") / len(non_space_characters)
        if non_space_characters
        else None
    )
    native_text_density = (
        native_characters / evidence.page_area
        if evidence.page_area and native_characters
        else None
    )
    raster_coverage = _coverage(evidence.raster_area, evidence.page_area)

    math_symbol_count = sum(character in _MATH_SYMBOLS for character in text)
    latex_token_count = len(_LATEX_TOKENS.findall(text))
    math_symbol_ratio = (
        math_symbol_count / len(non_space_characters) if non_space_characters else 0.0
    )
    formula_score = min(
        1.0,
        (0.50 if evidence.formula_count else 0.0)
        + min(evidence.formula_count, 3) * 0.10
        + min(math_symbol_ratio / 0.04, 1.0) * 0.25
        + min(latex_token_count, 2) * 0.10,
    )

    scientific_keyword_count = len(_SCIENTIFIC_TERMS.findall(text))
    scientific_score = min(
        1.0,
        min(scientific_keyword_count / 5, 1.0) * 0.70
        + (0.20 if evidence.column_count >= 2 else 0.0)
        + (0.10 if evidence.formula_count else 0.0),
    )

    complex_layout_score = min(
        1.0,
        (0.30 if evidence.column_count >= 2 else 0.0)
        + (0.25 if evidence.table_count else 0.0)
        + min(evidence.layout_regions / active_config.dense_layout_regions, 1.0) * 0.25
        + (0.20 if not evidence.reading_order_consistent else 0.0),
    )

    usable_native_text = (
        evidence.media_type in _NATIVE_DOCUMENT_MEDIA_TYPES
        and native_characters >= active_config.min_native_text_characters
        and native_alnum_ratio is not None
        and native_alnum_ratio >= active_config.min_native_alnum_ratio
        and replacement_ratio is not None
        and replacement_ratio <= active_config.max_replacement_character_ratio
        and evidence.reading_order_consistent
    )

    reasons = [
        (
            f"native_text_characters={native_characters} "
            f"(minimum={active_config.min_native_text_characters})"
        ),
        (
            "native_alnum_ratio="
            f"{_format_optional(native_alnum_ratio)} "
            f"(minimum={active_config.min_native_alnum_ratio:.3f})"
        ),
        (
            "replacement_character_ratio="
            f"{_format_optional(replacement_ratio)} "
            f"(maximum={active_config.max_replacement_character_ratio:.3f})"
        ),
        f"raster_coverage={_format_optional(raster_coverage)}",
        f"formula_score={formula_score:.3f}",
        f"scientific_score={scientific_score:.3f}",
        f"complex_layout_score={complex_layout_score:.3f}",
        f"reading_order_consistent={str(evidence.reading_order_consistent).lower()}",
    ]
    stored = ClassificationSignals(
        native_text_characters=native_characters,
        native_text_density=native_text_density,
        raster_coverage=raster_coverage,
        replacement_character_ratio=replacement_ratio,
        formula_score=formula_score,
        complex_layout_score=complex_layout_score,
        scientific_score=scientific_score,
        rotation_degrees=evidence.rotation_degrees % 360,
        reasons=reasons,
    )
    return MeasuredPageSignals(
        stored=stored,
        native_alnum_ratio=native_alnum_ratio,
        math_symbol_ratio=math_symbol_ratio,
        scientific_keyword_count=scientific_keyword_count,
        usable_native_text=usable_native_text,
        reading_order_consistent=evidence.reading_order_consistent,
        table_count=evidence.table_count,
        column_count=evidence.column_count,
        layout_regions=evidence.layout_regions,
    )


def classify_page(
    evidence: PageEvidence,
    *,
    config: ClassificationConfig | None = None,
    operator_parser: str | ParserRoute | None = None,
) -> RoutingDecision:
    active_config = config or ClassificationConfig()
    measured = measure_page_signals(evidence, config=active_config)
    signals = measured.stored
    reasons = list(signals.reasons)

    formula_scientific = (
        signals.formula_score >= active_config.formula_score_threshold
        or signals.scientific_score >= active_config.scientific_score_threshold
    )
    if formula_scientific:
        classification = PageClassification.FORMULA_HEAVY
        recommended_parser = ParserRoute.MINERU
        reasons.append(
            "formula/scientific threshold met; recommend mineru for formula preservation"
        )
    elif measured.usable_native_text or evidence.media_type in _OFFICE_MEDIA_TYPES:
        classification = PageClassification.DIGITAL
        recommended_parser = ParserRoute.DOCLING
        if measured.usable_native_text:
            reasons.append(
                "usable native text layer met character, plausibility, noise, and "
                "reading-order thresholds"
            )
        else:
            reasons.append(
                "native Office package retains its Docling extraction path; "
                "page-level output quality will determine any fallback"
            )
    else:
        image_input = evidence.media_type in _IMAGE_MEDIA_TYPES
        raster_scanned = (
            signals.raster_coverage is not None
            and signals.raster_coverage >= active_config.scanned_raster_coverage
        )
        complex_layout = (
            signals.complex_layout_score >= active_config.complex_layout_score_threshold
        )
        if complex_layout and (image_input or raster_scanned):
            classification = PageClassification.COMPLEX_LAYOUT
            recommended_parser = (
                ParserRoute.PADDLEOCR_VL
                if signals.complex_layout_score
                >= active_config.paddleocr_vl_score_threshold
                else ParserRoute.PADDLEOCR
            )
            reasons.append(
                "raster page met complex-layout threshold; recommend layout-aware OCR"
            )
        elif image_input or raster_scanned:
            classification = PageClassification.SCANNED
            recommended_parser = ParserRoute.PADDLEOCR
            reasons.append(
                "image input or raster coverage met scanned-page threshold; "
                "recommend paddleocr"
            )
        else:
            classification = PageClassification.UNKNOWN
            recommended_parser = ParserRoute.PADDLEOCR
            reasons.append(
                "native text is unusable and raster evidence is insufficient; "
                "recommend bounded OCR with manual review if quality remains uncertain"
            )

    override = _coerce_parser_route(operator_parser)
    operator_override = override is not None
    if override is not None:
        recommended_parser = override
        reasons.append(f"operator override selected parser={override.value}")

    return RoutingDecision(
        page_number=evidence.page_number,
        classification=classification,
        recommended_parser=recommended_parser,
        signals=signals,
        routing_reasons=tuple(reasons),
        operator_override=operator_override,
    )


def classify_document(
    pages: Sequence[PageEvidence],
    *,
    config: ClassificationConfig | None = None,
    operator_parsers: Mapping[int, str | ParserRoute] | None = None,
) -> DocumentClassification:
    if not pages:
        raise ValueError("at least one page is required")
    page_numbers = [page.page_number for page in pages]
    if len(page_numbers) != len(set(page_numbers)):
        raise ValueError("page numbers must be unique")

    overrides = operator_parsers or {}
    unknown_override_pages = set(overrides).difference(page_numbers)
    if unknown_override_pages:
        invalid = ", ".join(str(number) for number in sorted(unknown_override_pages))
        raise ValueError(f"operator override refers to unknown page(s): {invalid}")

    decisions = tuple(
        classify_page(
            page,
            config=config,
            operator_parser=overrides.get(page.page_number),
        )
        for page in sorted(pages, key=lambda item: item.page_number)
    )
    unique = {decision.classification.value for decision in decisions}
    mixed = len(unique) > 1
    classification = "mixed" if mixed else decisions[0].classification.value
    reasons = (
        (
            "page-level routing selected multiple classifications: "
            + ", ".join(sorted(unique))
        )
        if mixed
        else f"all pages classified as {classification}"
    )
    return DocumentClassification(
        classification=classification,
        page_decisions=decisions,
        mixed=mixed,
        routing_reasons=(reasons,),
    )


def _coverage(area: float | None, page_area: float | None) -> float | None:
    if area is None or page_area is None or page_area <= 0:
        return None
    return min(max(area / page_area, 0.0), 1.0)


def _format_optional(value: float | None) -> str:
    return "null" if value is None else f"{value:.3f}"


def _coerce_parser_route(
    parser: str | ParserRoute | None,
) -> ParserRoute | None:
    if parser is None:
        return None
    try:
        return ParserRoute(parser)
    except ValueError as exc:
        supported = ", ".join(route.value for route in ParserRoute)
        raise ValueError(
            f"Unsupported parser override {parser!r}; choose {supported}"
        ) from exc
