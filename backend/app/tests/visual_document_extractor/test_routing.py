from __future__ import annotations

import uuid

from app.visual_document_extractor.adapters import AdapterRole
from app.visual_document_extractor.models import (
    AdapterCapability,
    AdapterResult,
    AttemptStatus,
    ExtractedElement,
    ExtractionAttempt,
    PageClassification,
    PageInput,
)
from app.visual_document_extractor.quality import QualityPolicy
from app.visual_document_extractor.routing import ExtractionRouter, RoutingPolicy


class FakeAdapter:
    def __init__(
        self,
        name: str,
        technology: str,
        role: AdapterRole,
        results: list[AdapterResult],
    ) -> None:
        self.name = name
        self.version = "test"
        self.technology = technology
        self.role = role
        self.classifications = list(PageClassification)
        self._results = results
        self.calls = 0
        self.seen_pages: list[PageInput] = []

    def probe(self) -> AdapterCapability:
        return AdapterCapability(
            name=self.name,
            version=self.version,
            available=True,
            classifications=self.classifications,
        )

    def extract(self, page: PageInput) -> AdapterResult:
        self.seen_pages.append(page)
        index = min(self.calls, len(self._results) - 1)
        template = self._results[index]
        self.calls += 1
        return template.model_copy(
            update={
                "attempt": template.attempt.model_copy(update={"run_id": uuid.uuid4()})
            }
        )


def _page() -> PageInput:
    return PageInput(
        document_id=uuid.uuid4(),
        page_number=1,
        media_type="image/png",
        content=b"image",
        classification=PageClassification.SCANNED,
    )


def _result(
    parser: str,
    status: AttemptStatus,
    *,
    retryable: bool = False,
    text: str = "",
    model_derived: bool = False,
    confidence: float | None = None,
) -> AdapterResult:
    return AdapterResult(
        attempt=ExtractionAttempt(
            parser=parser,
            version="test",
            status=status,
            retryable=retryable,
            confidence=confidence,
            error_code=None if status is AttemptStatus.SUCCEEDED else "failed",
        ),
        elements=[
            ExtractedElement(
                element_id=f"{parser}-e1",
                text=text,
                reading_order=0,
                model_derived=model_derived,
            )
        ]
        if text
        else [],
    )


def test_low_quality_primary_uses_materially_different_fallback() -> None:
    primary = FakeAdapter(
        "paddleocr",
        "paddleocr",
        AdapterRole.PRIMARY,
        [_result("paddleocr", AttemptStatus.SUCCEEDED, text="")],
    )
    same_technology = FakeAdapter(
        "paddleocr-copy",
        "paddleocr",
        AdapterRole.SECONDARY,
        [_result("paddleocr-copy", AttemptStatus.SUCCEEDED, text="copy")],
    )
    secondary = FakeAdapter(
        "tesseract",
        "tesseract",
        AdapterRole.SECONDARY,
        [_result("tesseract", AttemptStatus.SUCCEEDED, text="Recovered text")],
    )

    outcome = ExtractionRouter([primary, same_technology, secondary]).extract(_page())

    assert outcome.manual_review_required is False
    assert outcome.selected_result is not None
    assert outcome.selected_result.attempt.parser == "tesseract"
    assert same_technology.calls == 0


def test_retry_and_fallback_caps_prevent_runaway_processing() -> None:
    transient = _result(
        "paddleocr",
        AttemptStatus.TIMEOUT,
        retryable=True,
    )
    failed = _result("failed", AttemptStatus.FAILED)
    primary = FakeAdapter("paddleocr", "paddleocr", AdapterRole.PRIMARY, [transient])
    alternates = [
        FakeAdapter(
            f"alternate-{index}", f"tech-{index}", AdapterRole.SECONDARY, [failed]
        )
        for index in range(4)
    ]
    visions = [
        FakeAdapter(f"vision-{index}", f"vision-{index}", AdapterRole.VISION, [failed])
        for index in range(3)
    ]
    policy = RoutingPolicy(
        transient_retries_per_adapter=1,
        max_alternate_attempts=2,
        max_vision_attempts=1,
    )

    outcome = ExtractionRouter(
        [primary, *alternates, *visions],
        policy=policy,
    ).extract(_page())

    assert primary.calls == 2
    assert sum(adapter.calls for adapter in alternates) == 2
    assert sum(adapter.calls for adapter in visions) == 1
    assert len(outcome.attempts) == 5
    assert outcome.manual_review_required is True


def test_vision_is_not_called_when_secondary_passes() -> None:
    primary = FakeAdapter(
        "paddleocr",
        "paddleocr",
        AdapterRole.PRIMARY,
        [_result("paddleocr", AttemptStatus.SUCCEEDED, text="")],
    )
    secondary = FakeAdapter(
        "secondary",
        "secondary",
        AdapterRole.SECONDARY,
        [_result("secondary", AttemptStatus.SUCCEEDED, text="Recovered")],
    )
    vision = FakeAdapter(
        "vision",
        "vision",
        AdapterRole.VISION,
        [
            _result(
                "vision",
                AttemptStatus.SUCCEEDED,
                text="Model text",
                model_derived=True,
            )
        ],
    )

    outcome = ExtractionRouter([primary, secondary, vision]).extract(_page())

    assert outcome.selected_result is not None
    assert outcome.selected_result.attempt.parser == "secondary"
    assert vision.calls == 0


def test_operator_can_override_initial_route_with_available_secondary() -> None:
    primary = FakeAdapter(
        "paddleocr",
        "paddleocr",
        AdapterRole.PRIMARY,
        [_result("paddleocr", AttemptStatus.SUCCEEDED, text="Primary")],
    )
    secondary = FakeAdapter(
        "secondary",
        "secondary",
        AdapterRole.SECONDARY,
        [_result("secondary", AttemptStatus.SUCCEEDED, text="Overridden")],
    )
    page = _page().model_copy(update={"operator_parser": "secondary"})

    outcome = ExtractionRouter([primary, secondary]).extract(page)

    assert outcome.selected_result is not None
    assert outcome.selected_result.attempt.parser == "secondary"
    assert primary.calls == 0
    assert "operator_override=secondary" in outcome.routing_reasons


def test_remote_chain_escalates_mistral_then_terra_then_sol() -> None:
    local = FakeAdapter(
        "tesseract",
        "tesseract",
        AdapterRole.SECONDARY,
        [
            _result(
                "tesseract",
                AttemptStatus.SUCCEEDED,
                text="Low confidence local text",
                confidence=0.60,
            )
        ],
    )
    mistral = FakeAdapter(
        "mistral-ocr",
        "vision:mistral",
        AdapterRole.VISION,
        [
            _result(
                "mistral-ocr",
                AttemptStatus.SUCCEEDED,
                text="Low confidence Mistral text",
                confidence=0.70,
            )
        ],
    )
    terra = FakeAdapter(
        "openai-vision-terra",
        "vision:openai:terra",
        AdapterRole.VISION,
        [_result("openai-vision-terra", AttemptStatus.FAILED)],
    )
    sol = FakeAdapter(
        "openai-vision-sol",
        "vision:openai:sol",
        AdapterRole.VISION,
        [
            _result(
                "openai-vision-sol",
                AttemptStatus.SUCCEEDED,
                text="Grounded extraction from difficult page",
                model_derived=True,
            )
        ],
    )
    router = ExtractionRouter(
        [local, mistral, terra, sol],
        policy=RoutingPolicy(max_alternate_attempts=1, max_vision_attempts=3),
        quality_policy=QualityPolicy(minimum_confidence=0.80),
    )

    outcome = router.extract(_page())

    assert outcome.selected_result is not None
    assert outcome.selected_result.attempt.parser == "openai-vision-sol"
    assert [mistral.calls, terra.calls, sol.calls] == [1, 1, 1]
    assert terra.seen_pages[0].fallback_context[0]["parser"] == "tesseract"
    assert len(sol.seen_pages[0].fallback_context) == 3


def test_terra_sensitive_value_disagreement_escalates_to_sol() -> None:
    local = FakeAdapter(
        "tesseract",
        "tesseract",
        AdapterRole.SECONDARY,
        [
            _result(
                "tesseract",
                AttemptStatus.SUCCEEDED,
                text="Invoice total $52.40",
                confidence=0.60,
            )
        ],
    )
    mistral = FakeAdapter(
        "mistral-ocr",
        "vision:mistral",
        AdapterRole.VISION,
        [
            _result(
                "mistral-ocr",
                AttemptStatus.SUCCEEDED,
                text="Invoice total $52.40",
                confidence=0.70,
            )
        ],
    )
    terra = FakeAdapter(
        "openai-vision-terra",
        "vision:openai:terra",
        AdapterRole.VISION,
        [
            _result(
                "openai-vision-terra",
                AttemptStatus.SUCCEEDED,
                text="Invoice total $52.90",
                model_derived=True,
            )
        ],
    )
    sol = FakeAdapter(
        "openai-vision-sol",
        "vision:openai:sol",
        AdapterRole.VISION,
        [
            _result(
                "openai-vision-sol",
                AttemptStatus.SUCCEEDED,
                text="Invoice total $52.40",
                model_derived=True,
            )
        ],
    )
    router = ExtractionRouter(
        [local, mistral, terra, sol],
        policy=RoutingPolicy(max_alternate_attempts=1, max_vision_attempts=3),
        quality_policy=QualityPolicy(minimum_confidence=0.80),
    )

    outcome = router.extract(_page())

    assert outcome.selected_result is not None
    assert outcome.selected_result.attempt.parser == "openai-vision-sol"
    terra_attempt = next(
        attempt
        for attempt in outcome.attempts
        if attempt.parser == "openai-vision-terra"
    )
    signal = next(
        item
        for item in terra_attempt.quality_signals
        if item.name == "sensitive_value_agreement"
    )
    assert signal.passed is False
