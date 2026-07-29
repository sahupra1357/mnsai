from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from ..adapter_workers import (
    configured_command_executor,
    tesseract_available,
    tesseract_executor,
    tesseract_version,
)
from ..execution import ProcessLimits
from ..models import (
    AdapterResult,
    PageClassification,
)
from ..remote_workers import (
    mistral_ocr_executor,
    openai_sol_executor,
    openai_terra_executor,
)
from .base import AdapterExecutor, AdapterRole, OptionalDependencyAdapter


class ConfigurableCommandAdapter(OptionalDependencyAdapter):
    command_environment_variable = ""

    def __init__(
        self,
        *,
        executor: AdapterExecutor | None = None,
        version: str | None = None,
        process_limits: ProcessLimits | None = None,
    ) -> None:
        configured = configured_command_executor(self.command_environment_variable)
        super().__init__(
            executor=executor or configured,
            version=version,
            process_limits=process_limits,
        )


class DoclingAdapter(ConfigurableCommandAdapter):
    name = "docling"
    technology = "docling"
    dependency_modules = ("docling",)
    dependency_distribution = "docling"
    command_environment_variable = "VISUAL_EXTRACTOR_DOCLING_WORKER"
    classifications: Sequence[PageClassification] = (
        PageClassification.DIGITAL,
        PageClassification.UNKNOWN,
    )


class PaddleOCRAdapter(ConfigurableCommandAdapter):
    name = "paddleocr"
    technology = "paddleocr"
    dependency_modules = ("paddleocr",)
    dependency_distribution = "paddleocr"
    command_environment_variable = "VISUAL_EXTRACTOR_PADDLEOCR_WORKER"
    classifications: Sequence[PageClassification] = (
        PageClassification.SCANNED,
        PageClassification.UNKNOWN,
    )


class PaddleOCRVLAdapter(ConfigurableCommandAdapter):
    name = "paddleocr-vl"
    technology = "paddleocr-vl"
    dependency_modules = ("paddleocr",)
    dependency_distribution = "paddleocr"
    command_environment_variable = "VISUAL_EXTRACTOR_PADDLEOCR_VL_WORKER"
    classifications: Sequence[PageClassification] = (
        PageClassification.COMPLEX_LAYOUT,
        PageClassification.SCANNED,
    )


class MinerUAdapter(ConfigurableCommandAdapter):
    name = "mineru"
    technology = "mineru"
    dependency_modules = ("mineru",)
    dependency_distribution = "mineru"
    command_environment_variable = "VISUAL_EXTRACTOR_MINERU_WORKER"
    classifications: Sequence[PageClassification] = (
        PageClassification.FORMULA_HEAVY,
        PageClassification.COMPLEX_LAYOUT,
    )


class MarkerAdapter(ConfigurableCommandAdapter):
    name = "marker"
    technology = "marker"
    dependency_modules = ("marker",)
    dependency_distribution = "marker-pdf"
    command_environment_variable = "VISUAL_EXTRACTOR_MARKER_WORKER"
    classifications: Sequence[PageClassification] = (
        PageClassification.FORMULA_HEAVY,
        PageClassification.COMPLEX_LAYOUT,
    )


class SecondaryOCRAdapter(OptionalDependencyAdapter):
    name = "tesseract"
    technology = "tesseract"
    role = AdapterRole.SECONDARY
    dependency_modules = ()
    dependency_distribution = None
    classifications: Sequence[PageClassification] = tuple(PageClassification)

    def __init__(
        self,
        *,
        executor: AdapterExecutor | None = None,
        version: str | None = None,
        process_limits: ProcessLimits | None = None,
    ) -> None:
        super().__init__(
            executor=executor
            or (tesseract_executor if tesseract_available() else None),
            version=version or tesseract_version(),
            process_limits=process_limits,
        )


class VisionModelAdapter(OptionalDependencyAdapter):
    name = "vision-model"
    role = AdapterRole.VISION
    classifications: Sequence[PageClassification] = tuple(PageClassification)

    def __init__(
        self,
        *,
        provider: str = "unconfigured",
        model: str = "unconfigured",
        prompt_version: str = "v1",
        executor: AdapterExecutor | None = None,
        version: str | None = None,
        process_limits: ProcessLimits | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.prompt_version = prompt_version
        self.technology = f"vision:{provider}"
        super().__init__(
            executor=executor,
            version=version or model,
            process_limits=process_limits,
        )

    def _normalize_result(
        self,
        result: AdapterResult,
        *,
        started_at: datetime,
    ) -> AdapterResult:
        normalized = super()._normalize_result(result, started_at=started_at)
        attempt = normalized.attempt.model_copy(
            update={
                "provider": self.provider,
                "model": self.model,
                "prompt_version": self.prompt_version,
            }
        )
        elements = [
            element.model_copy(update={"model_derived": True})
            for element in normalized.elements
        ]
        return normalized.model_copy(update={"attempt": attempt, "elements": elements})

    def _failure_result(self, **kwargs: object) -> AdapterResult:
        result = super()._failure_result(**kwargs)  # type: ignore[arg-type]
        attempt = result.attempt.model_copy(
            update={
                "provider": self.provider,
                "model": self.model,
                "prompt_version": self.prompt_version,
            }
        )
        return result.model_copy(update={"attempt": attempt})


class MistralOCRAdapter(VisionModelAdapter):
    name = "mistral-ocr"
    technology = "vision:mistral-ocr-4"

    def __init__(
        self,
        *,
        enabled: bool = False,
        api_key_configured: bool = False,
        model: str = "mistral-ocr-4-0",
        process_limits: ProcessLimits | None = None,
        executor: AdapterExecutor | None = None,
    ) -> None:
        selected_executor = executor
        if selected_executor is None and enabled and api_key_configured:
            selected_executor = mistral_ocr_executor
        super().__init__(
            provider="mistral",
            model=model,
            prompt_version="ocr-api-v1",
            executor=selected_executor,
            version=model,
            process_limits=process_limits,
        )
        self.technology = "vision:mistral-ocr-4"


class OpenAIVisionAdapter(VisionModelAdapter):
    def __init__(
        self,
        *,
        name: str,
        model: str,
        enabled: bool = False,
        api_key_configured: bool = False,
        executor: AdapterExecutor | None = None,
        process_limits: ProcessLimits | None = None,
    ) -> None:
        self.name = name
        selected_executor = executor
        if selected_executor is None and enabled and api_key_configured:
            selected_executor = (
                openai_sol_executor if name.endswith("-sol") else openai_terra_executor
            )
        super().__init__(
            provider="openai",
            model=model,
            prompt_version="visual-page-v1",
            executor=selected_executor,
            version=model,
            process_limits=process_limits,
        )
        self.technology = f"vision:openai:{model}"
