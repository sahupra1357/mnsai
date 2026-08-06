from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from .adapters import AdapterRole, ExtractionAdapter
from .models import (
    AdapterCapability,
    AdapterResult,
    ExtractionAttempt,
    PageClassification,
    PageInput,
    QualitySignal,
)
from .quality import (
    QualityAssessment,
    QualityPolicy,
    choose_best_candidate,
    validate_result,
)


@dataclass(frozen=True)
class RoutingPolicy:
    transient_retries_per_adapter: int = 1
    max_alternate_attempts: int = 2
    max_vision_attempts: int = 1

    def __post_init__(self) -> None:
        for value, name in (
            (
                self.transient_retries_per_adapter,
                "transient_retries_per_adapter",
            ),
            (self.max_alternate_attempts, "max_alternate_attempts"),
            (self.max_vision_attempts, "max_vision_attempts"),
        ):
            if value < 0:
                raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True)
class RoutingOutcome:
    selected_result: AdapterResult | None
    attempts: tuple[ExtractionAttempt, ...]
    assessment: QualityAssessment | None
    manual_review_required: bool
    routing_reasons: tuple[str, ...]


_ROUTE_PREFERENCES: dict[PageClassification, tuple[str, ...]] = {
    PageClassification.DIGITAL: ("docling",),
    PageClassification.SCANNED: ("paddleocr", "paddleocr-vl"),
    PageClassification.FORMULA_HEAVY: ("mineru", "marker"),
    PageClassification.COMPLEX_LAYOUT: ("paddleocr-vl", "mineru", "marker"),
    PageClassification.UNKNOWN: ("docling", "paddleocr"),
}


class ExtractionRouter:
    def __init__(
        self,
        adapters: Sequence[ExtractionAdapter],
        *,
        policy: RoutingPolicy | None = None,
        quality_policy: QualityPolicy | None = None,
    ) -> None:
        names = [adapter.name for adapter in adapters]
        if len(names) != len(set(names)):
            raise ValueError("Adapter names must be unique")
        self._adapters = tuple(adapters)
        self.policy = policy or RoutingPolicy()
        self.quality_policy = quality_policy or QualityPolicy()

    def capabilities(self) -> list[AdapterCapability]:
        return [adapter.probe() for adapter in self._adapters]

    def extract(self, page: PageInput) -> RoutingOutcome:
        attempts: list[ExtractionAttempt] = []
        candidates: list[AdapterResult] = []
        assessments: dict[str, QualityAssessment] = {}
        routing_reasons = [
            f"page_classification={page.classification.value}",
        ]
        available = [
            adapter
            for adapter in self._adapters
            if self._is_available_for(adapter, page)
        ]

        primary = self._select_primary(available, page)
        used_technologies: set[str] = set()
        if primary is not None:
            if page.operator_parser:
                routing_reasons.append(f"operator_override={page.operator_parser}")
            routing_reasons.append(f"primary={primary.name}")
            used_technologies.add(primary.technology)
            retries_remaining = self.policy.transient_retries_per_adapter
            while True:
                result, assessment = self._run(primary, page)
                attempts.append(result.attempt)
                candidates.append(result)
                assessments[str(result.attempt.run_id)] = assessment
                if assessment.passed:
                    return self._successful_outcome(
                        result,
                        attempts,
                        assessment,
                        routing_reasons,
                    )
                if not result.attempt.retryable or retries_remaining == 0:
                    break
                retries_remaining -= 1
                routing_reasons.append(f"transient_retry={primary.name}")
        else:
            routing_reasons.append("primary=unavailable")

        alternate_budget = self.policy.max_alternate_attempts
        for alternate in self._ordered_by_role(available, AdapterRole.SECONDARY):
            if alternate_budget == 0:
                break
            if alternate.technology in used_technologies:
                routing_reasons.append(f"skipped_same_technology={alternate.name}")
                continue
            used_technologies.add(alternate.technology)
            retries_remaining = self.policy.transient_retries_per_adapter
            while alternate_budget > 0:
                result, assessment = self._run(alternate, page)
                alternate_budget -= 1
                attempts.append(result.attempt)
                candidates.append(result)
                assessments[str(result.attempt.run_id)] = assessment
                routing_reasons.append(f"alternate={alternate.name}")
                if assessment.passed:
                    return self._successful_outcome(
                        result,
                        attempts,
                        assessment,
                        routing_reasons,
                    )
                if not result.attempt.retryable or retries_remaining == 0:
                    break
                retries_remaining -= 1
                routing_reasons.append(f"transient_retry={alternate.name}")

        vision_budget = self.policy.max_vision_attempts
        for vision in self._ordered_by_role(available, AdapterRole.VISION):
            if vision_budget == 0:
                break
            if vision.technology in used_technologies:
                continue
            used_technologies.add(vision.technology)
            vision_page = page.model_copy(
                update={
                    "fallback_context": self._fallback_context(candidates, assessments)
                }
            )
            result, assessment = self._run(vision, vision_page)
            if vision.name == "openai-vision-terra":
                assessment = self._terra_candidate_check(result, candidates, assessment)
                result = result.model_copy(
                    update={
                        "attempt": result.attempt.model_copy(
                            update={"quality_signals": list(assessment.signals)}
                        )
                    }
                )
            vision_budget -= 1
            attempts.append(result.attempt)
            candidates.append(result)
            assessments[str(result.attempt.run_id)] = assessment
            routing_reasons.append(f"vision={vision.name}")
            if assessment.passed:
                return self._successful_outcome(
                    result,
                    attempts,
                    assessment,
                    routing_reasons,
                )

        selected = choose_best_candidate(page, candidates, self.quality_policy)
        selected_assessment = (
            assessments.get(str(selected.attempt.run_id))
            if selected is not None
            else None
        )
        routing_reasons.append("terminal=manual_review_required")
        return RoutingOutcome(
            selected_result=selected,
            attempts=tuple(attempts),
            assessment=selected_assessment,
            manual_review_required=True,
            routing_reasons=tuple(routing_reasons),
        )

    @staticmethod
    def _fallback_context(
        candidates: list[AdapterResult],
        assessments: dict[str, QualityAssessment],
    ) -> list[dict[str, object]]:
        context: list[dict[str, object]] = []
        for candidate in candidates:
            assessment = assessments.get(str(candidate.attempt.run_id))
            context.append(
                {
                    "parser": candidate.attempt.parser,
                    "model": candidate.attempt.model,
                    "confidence": candidate.attempt.confidence,
                    "failed_checks": (
                        sorted(assessment.failed_checks) if assessment else []
                    ),
                    "elements": [
                        {
                            "type": element.type,
                            "text": element.text,
                            "reading_order": element.reading_order,
                            "bounding_box": (
                                element.bounding_box.model_dump()
                                if element.bounding_box is not None
                                else None
                            ),
                        }
                        for element in candidate.elements
                    ],
                }
            )
        return context

    @staticmethod
    def _terra_candidate_check(
        result: AdapterResult,
        prior_candidates: list[AdapterResult],
        assessment: QualityAssessment,
    ) -> QualityAssessment:
        """Escalate material sensitive-value disagreements for Sol adjudication."""

        pattern = re.compile(
            r"(?:https?://\S+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|"
            r"\b\d[\d.,:/%$€£+-]*\b|\b(?:not|no|never)\b)",
            re.IGNORECASE,
        )
        current_text = "\n".join(element.text for element in result.elements)
        current = {value.casefold() for value in pattern.findall(current_text)}
        previous: set[str] = set()
        for candidate in reversed(prior_candidates):
            text = "\n".join(element.text for element in candidate.elements)
            values = {value.casefold() for value in pattern.findall(text)}
            if values:
                previous = values
                break
        passed: bool | None = None if not previous else current == previous
        signal = QualitySignal(
            name="sensitive_value_agreement",
            passed=passed,
            value=len(current),
            threshold=len(previous) if previous else None,
            detail=(
                "Terra disagrees with the preceding parser on a number, "
                "identifier, URL, email, or negation"
                if passed is False
                else None
            ),
        )
        signals = (*assessment.signals, signal)
        definitive = [item for item in signals if item.passed is not None]
        passed_count = sum(item.passed is True for item in definitive)
        return QualityAssessment(
            passed=assessment.passed and passed is not False,
            score=passed_count / len(definitive) if definitive else 0,
            signals=signals,
            warnings=(
                *assessment.warnings,
                *((signal.detail,) if signal.passed is False and signal.detail else ()),
            ),
        )

    def _is_available_for(
        self,
        adapter: ExtractionAdapter,
        page: PageInput,
    ) -> bool:
        capability = adapter.probe()
        return capability.available and (
            not capability.classifications
            or page.classification in capability.classifications
        )

    def _select_primary(
        self,
        adapters: Sequence[ExtractionAdapter],
        page: PageInput,
    ) -> ExtractionAdapter | None:
        primary = [
            adapter for adapter in adapters if adapter.role is AdapterRole.PRIMARY
        ]
        if page.operator_parser:
            return next(
                (
                    adapter
                    for adapter in adapters
                    if adapter.name == page.operator_parser
                ),
                None,
            )
        preferences = _ROUTE_PREFERENCES[page.classification]
        by_name = {adapter.name: adapter for adapter in primary}
        for name in preferences:
            if name in by_name:
                return by_name[name]
        return primary[0] if primary else None

    @staticmethod
    def _ordered_by_role(
        adapters: Sequence[ExtractionAdapter],
        role: AdapterRole,
    ) -> list[ExtractionAdapter]:
        return [adapter for adapter in adapters if adapter.role is role]

    def _run(
        self,
        adapter: ExtractionAdapter,
        page: PageInput,
    ) -> tuple[AdapterResult, QualityAssessment]:
        result = adapter.extract(page)
        assessment = validate_result(page, result, self.quality_policy)
        attempt = result.attempt.model_copy(
            update={"quality_signals": list(assessment.signals)}
        )
        normalized = result.model_copy(update={"attempt": attempt})
        return normalized, assessment

    @staticmethod
    def _successful_outcome(
        result: AdapterResult,
        attempts: list[ExtractionAttempt],
        assessment: QualityAssessment,
        routing_reasons: list[str],
    ) -> RoutingOutcome:
        routing_reasons.append(f"selected={result.attempt.parser}")
        return RoutingOutcome(
            selected_result=result,
            attempts=tuple(attempts),
            assessment=assessment,
            manual_review_required=False,
            routing_reasons=tuple(routing_reasons),
        )
