from __future__ import annotations

from dataclasses import dataclass
from unicodedata import category

from .models import (
    AdapterResult,
    AttemptStatus,
    PageClassification,
    PageInput,
    QualitySignal,
)


@dataclass(frozen=True)
class QualityPolicy:
    min_text_characters: int = 8
    max_replacement_character_ratio: float = 0.05
    max_control_character_ratio: float = 0.01
    minimum_confidence: float | None = 0.5

    def __post_init__(self) -> None:
        if self.min_text_characters < 0:
            raise ValueError("min_text_characters must be non-negative")
        for value, name in (
            (
                self.max_replacement_character_ratio,
                "max_replacement_character_ratio",
            ),
            (self.max_control_character_ratio, "max_control_character_ratio"),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.minimum_confidence is not None and not (
            0 <= self.minimum_confidence <= 1
        ):
            raise ValueError("minimum_confidence must be between 0 and 1")


@dataclass(frozen=True)
class QualityAssessment:
    passed: bool
    score: float
    signals: tuple[QualitySignal, ...]
    warnings: tuple[str, ...] = ()

    @property
    def failed_checks(self) -> set[str]:
        return {
            signal.name for signal in self.signals if signal.passed is False
        }


def _signal(
    name: str,
    passed: bool | None,
    *,
    value: float | int | str | bool | None = None,
    threshold: float | int | str | bool | None = None,
    detail: str | None = None,
) -> QualitySignal:
    return QualitySignal(
        name=name,
        passed=passed,
        value=value,
        threshold=threshold,
        detail=detail,
    )


def validate_result(
    page: PageInput,
    result: AdapterResult,
    policy: QualityPolicy | None = None,
) -> QualityAssessment:
    policy = policy or QualityPolicy()
    signals: list[QualitySignal] = []

    successful = result.attempt.status is AttemptStatus.SUCCEEDED
    signals.append(
        _signal(
            "attempt_status",
            successful,
            value=result.attempt.status.value,
            threshold=AttemptStatus.SUCCEEDED.value,
        )
    )

    joined_text = "\n".join(element.text for element in result.elements)
    text_length = len(joined_text.strip())
    signals.append(
        _signal(
            "minimum_text",
            text_length >= policy.min_text_characters,
            value=text_length,
            threshold=policy.min_text_characters,
        )
    )

    denominator = max(len(joined_text), 1)
    replacement_ratio = joined_text.count("\ufffd") / denominator
    signals.append(
        _signal(
            "replacement_characters",
            replacement_ratio <= policy.max_replacement_character_ratio,
            value=replacement_ratio,
            threshold=policy.max_replacement_character_ratio,
        )
    )

    control_count = sum(
        1
        for character in joined_text
        if category(character).startswith("C")
        and character not in {"\n", "\r", "\t"}
    )
    control_ratio = control_count / denominator
    signals.append(
        _signal(
            "control_characters",
            control_ratio <= policy.max_control_character_ratio,
            value=control_ratio,
            threshold=policy.max_control_character_ratio,
        )
    )

    reading_orders = [element.reading_order for element in result.elements]
    reading_order_valid = (
        len(reading_orders) == len(set(reading_orders))
        and reading_orders == sorted(reading_orders)
    )
    signals.append(
        _signal(
            "reading_order",
            reading_order_valid,
            value=len(reading_orders),
            detail="Reading order must be unique and monotonic",
        )
    )

    element_ids = [element.element_id for element in result.elements]
    signals.append(
        _signal(
            "element_ids",
            len(element_ids) == len(set(element_ids)),
            value=len(element_ids),
            detail="Element IDs must be unique within a page",
        )
    )

    coordinates_valid = True
    coordinate_detail: str | None = None
    for element in result.elements:
        if element.bounding_box is None:
            continue
        space = element.coordinate_space or page.coordinate_space
        if space is None:
            coordinates_valid = False
            coordinate_detail = "Bounding box has no declared coordinate space"
            break
        box = element.bounding_box
        if (
            box.left < 0
            or box.top < 0
            or box.right > space.width
            or box.bottom > space.height
        ):
            coordinates_valid = False
            coordinate_detail = "Bounding box falls outside its coordinate space"
            break
    signals.append(
        _signal(
            "coordinates",
            coordinates_valid,
            detail=coordinate_detail,
        )
    )

    table_elements = [
        element for element in result.elements if element.type == "table"
    ]
    if table_elements:
        usable_table = all(element.text.strip() for element in table_elements)
        signals.append(
            _signal(
                "table_structure",
                usable_table,
                value=len(table_elements),
                detail="Detected table elements must contain usable content",
            )
        )

    if page.classification is PageClassification.FORMULA_HEAVY:
        formula_elements = [
            element
            for element in result.elements
            if element.type == "formula" and element.text.strip()
        ]
        signals.append(
            _signal(
                "formula_presence",
                bool(formula_elements),
                value=len(formula_elements),
                threshold=1,
            )
        )

    confidence = result.attempt.confidence
    if confidence is None:
        signals.append(
            _signal(
                "confidence",
                None,
                detail="Parser did not provide calibrated confidence",
            )
        )
    elif policy.minimum_confidence is None:
        signals.append(_signal("confidence", None, value=confidence))
    else:
        signals.append(
            _signal(
                "confidence",
                confidence >= policy.minimum_confidence,
                value=confidence,
                threshold=policy.minimum_confidence,
            )
        )

    definitive = [signal for signal in signals if signal.passed is not None]
    passed_count = sum(signal.passed is True for signal in definitive)
    score = passed_count / len(definitive) if definitive else 0.0
    passed = bool(definitive) and all(
        signal.passed is not False for signal in signals
    )
    warnings = tuple(
        signal.detail
        for signal in signals
        if signal.passed is False and signal.detail
    )
    return QualityAssessment(
        passed=passed,
        score=score,
        signals=tuple(signals),
        warnings=warnings,
    )


def choose_best_candidate(
    page: PageInput,
    candidates: list[AdapterResult],
    policy: QualityPolicy | None = None,
) -> AdapterResult | None:
    if not candidates:
        return None
    policy = policy or QualityPolicy()

    def rank(result: AdapterResult) -> tuple[int, float, float, int]:
        assessment = validate_result(page, result, policy)
        confidence = (
            result.attempt.confidence
            if result.attempt.confidence is not None
            else -1.0
        )
        text_length = sum(len(element.text.strip()) for element in result.elements)
        return (
            int(assessment.passed),
            assessment.score,
            confidence,
            text_length,
        )

    return max(candidates, key=rank)
