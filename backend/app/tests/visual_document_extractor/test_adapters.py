from __future__ import annotations

import uuid

from app.visual_document_extractor.adapters import (
    DoclingAdapter,
    PaddleOCRAdapter,
    VisionModelAdapter,
)
from app.visual_document_extractor.models import (
    AdapterResult,
    AttemptStatus,
    ExtractedElement,
    ExtractionAttempt,
    PageClassification,
    PageInput,
)


def _page() -> PageInput:
    return PageInput(
        document_id=uuid.uuid4(),
        page_number=1,
        media_type="application/pdf",
        content=b"%PDF",
        classification=PageClassification.DIGITAL,
    )


def _success(parser: str, version: str) -> AdapterResult:
    return AdapterResult(
        attempt=ExtractionAttempt(
            parser=parser,
            version=version,
            status=AttemptStatus.SUCCEEDED,
            confidence=0.98,
        ),
        elements=[
            ExtractedElement(
                element_id="p1-e1",
                text="Native text",
                reading_order=0,
                confidence=0.98,
                confidence_source="parser",
            )
        ],
    )


def test_optional_adapter_probe_does_not_import_dependency(monkeypatch) -> None:
    imported: list[str] = []

    monkeypatch.setattr(
        "app.visual_document_extractor.adapters.base.importlib.util.find_spec",
        lambda name: None,
    )
    monkeypatch.setattr(
        "app.visual_document_extractor.adapters.base.importlib.import_module",
        lambda name: imported.append(name),
    )

    capability = DoclingAdapter().probe()

    assert capability.available is False
    assert "not installed" in (capability.reason or "")
    assert imported == []


def test_configured_adapter_returns_normalized_result() -> None:
    adapter = PaddleOCRAdapter(
        executor=lambda page: _success("paddleocr", "test-version"),
        version="test-version",
    )

    result = adapter.extract(_page())

    assert adapter.probe().available is True
    assert result.attempt.parser == "paddleocr"
    assert result.attempt.status is AttemptStatus.SUCCEEDED


def test_provider_exception_is_converted_to_safe_structured_failure() -> None:
    def explode(_page_input: PageInput) -> AdapterResult:
        raise RuntimeError("secret provider payload")

    result = DoclingAdapter(executor=explode).extract(_page())

    assert result.attempt.status is AttemptStatus.FAILED
    assert result.attempt.error_code == "adapter_execution_failed"
    assert result.attempt.retryable is False
    assert "secret provider payload" not in (result.attempt.error_message or "")


def test_invalid_executor_output_is_rejected_at_contract_boundary() -> None:
    adapter = DoclingAdapter(executor=lambda page: {"unexpected": page.page_number})  # type: ignore[arg-type,return-value]

    result = adapter.extract(_page())

    assert result.attempt.status is AttemptStatus.FAILED
    assert result.attempt.error_code == "invalid_adapter_output"


def test_unconfigured_vision_adapter_reports_unavailable() -> None:
    adapter = VisionModelAdapter(provider="example", model="vision-1")

    result = adapter.extract(_page())

    assert adapter.probe().available is False
    assert result.attempt.status is AttemptStatus.UNAVAILABLE
    assert result.attempt.provider == "example"
    assert result.attempt.model == "vision-1"


def test_vision_output_is_labeled_with_model_provenance() -> None:
    adapter = VisionModelAdapter(
        provider="example",
        model="vision-1",
        prompt_version="schema-v2",
        executor=lambda _page_input: _success(
            "provider-native-name", "provider-version"
        ),
    )

    result = adapter.extract(_page())

    assert result.attempt.provider == "example"
    assert result.attempt.model == "vision-1"
    assert result.attempt.prompt_version == "schema-v2"
    assert all(element.model_derived for element in result.elements)
