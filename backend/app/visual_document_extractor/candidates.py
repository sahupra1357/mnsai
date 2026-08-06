from __future__ import annotations

from .models import (
    AdapterResult,
    ExtractionCandidate,
    PageResult,
    ParserSelection,
)


def result_confidence(result: AdapterResult) -> float | None:
    if result.attempt.confidence is not None:
        return result.attempt.confidence
    values = [
        element.confidence
        for element in result.elements
        if element.confidence is not None
    ]
    return sum(values) / len(values) if values else None


def add_candidate(
    page: PageResult,
    result: AdapterResult,
    *,
    quality_passed: bool,
    rationale: str,
) -> ExtractionCandidate | None:
    if not result.elements:
        return None
    for existing in page.candidates:
        if existing.parser.run_id == result.attempt.run_id:
            return existing
    confidence = result_confidence(result)
    candidate = ExtractionCandidate(
        parser=ParserSelection(
            name=result.attempt.parser,
            version=result.attempt.version,
            run_id=result.attempt.run_id,
            rationale=rationale,
        ),
        confidence=confidence,
        confidence_source=(
            f"{result.attempt.parser}:page_mean" if confidence is not None else None
        ),
        quality_passed=quality_passed,
        elements=result.elements,
        warnings=result.warnings,
    )
    page.candidates.append(candidate)
    return candidate


def preserve_current_candidate(page: PageResult) -> ExtractionCandidate | None:
    """Backfill the active result for documents created before candidate history."""
    if page.selected_parser is None or not page.elements:
        return None
    for existing in page.candidates:
        if existing.parser.run_id == page.selected_parser.run_id:
            return existing
    candidate = ExtractionCandidate(
        parser=page.selected_parser.model_copy(deep=True),
        confidence=page.confidence,
        confidence_source=page.confidence_source,
        quality_passed=page.page_status.value not in {"failed", "manual_review_required"},
        elements=[element.model_copy(deep=True) for element in page.elements],
        warnings=list(page.warnings),
    )
    page.candidates.append(candidate)
    page.selected_candidate_id = candidate.candidate_id
    return candidate


def best_candidate(page: PageResult) -> ExtractionCandidate | None:
    if not page.candidates:
        return None
    return max(
        page.candidates,
        key=lambda candidate: (
            candidate.quality_passed,
            candidate.confidence is not None,
            candidate.confidence if candidate.confidence is not None else -1.0,
            candidate.created_at,
        ),
    )


def select_best_candidate(page: PageResult) -> ExtractionCandidate | None:
    candidate = best_candidate(page)
    if candidate is None:
        return None
    page.selected_candidate_id = candidate.candidate_id
    page.selected_parser = candidate.parser.model_copy(deep=True)
    page.confidence = candidate.confidence
    page.confidence_source = candidate.confidence_source
    page.elements = [element.model_copy(deep=True) for element in candidate.elements]
    page.warnings = list(candidate.warnings)
    return candidate
