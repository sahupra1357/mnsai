"""Grounded semantic structuring of already-extracted page content.

The structurer proposes labels and values; this module decides what is allowed into
the clean export. Semantic failures never trigger another OCR/parser run.
"""

from __future__ import annotations

import re
import unicodedata
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from .models import ExtractedElement


class GroundingStatus(str, Enum):
    GROUNDED = "grounded"
    GROUNDED_WITH_NORMALIZATION = "grounded_with_normalization"
    NEEDS_REVIEW = "needs_review"
    REJECTED_INVALID_REFERENCE = "rejected_invalid_reference"
    REJECTED_UNGROUNDED = "rejected_ungrounded"
    REJECTED_SENSITIVE_MISMATCH = "rejected_sensitive_mismatch"
    REJECTED_OVERLAP = "rejected_overlap"


class SemanticCandidate(BaseModel):
    candidate_id: str
    key: str
    value: str
    source_element_ids: list[str] = Field(min_length=1)
    source_order: int = Field(ge=0)


class CandidateVerification(BaseModel):
    candidate_id: str
    status: GroundingStatus
    grounding_score: float = Field(ge=0, le=1)
    detail: str | None = None


class CoverageEntry(BaseModel):
    element_id: str
    status: Literal["consumed", "unclassified", "ignored_non_text"]
    candidate_id: str | None = None


class SemanticResult(BaseModel):
    mode: Literal["deterministic", "verified_ai", "hybrid"]
    schema_version: Literal["1"] = "1"
    structurer_provider: str | None = None
    structurer_model: str | None = None
    prompt_version: str | None = None
    candidates: list[SemanticCandidate] = Field(default_factory=list)
    verifications: list[CandidateVerification] = Field(default_factory=list)
    coverage: list[CoverageEntry] = Field(default_factory=list)
    final_content: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


_SENSITIVE = re.compile(
    r"(?:https?://\S+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b\d[\d.,:/%$€£+-]*\b|\b(?:not|no|never)\b)",
    re.IGNORECASE,
)


def _normalized(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("‐", "-").replace("‑", "-").replace("–", "-")
    value = re.sub(r"-\s*\n\s*", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" \t\r\n\"'“”‘’")


def _tokens(value: str) -> list[str]:
    return re.findall(r"\w+|[^\w\s]", _normalized(value).casefold())


def verify_candidate(
    candidate: SemanticCandidate,
    elements: list[ExtractedElement],
) -> CandidateVerification:
    by_id = {element.element_id: element for element in elements}
    if len(set(candidate.source_element_ids)) != len(candidate.source_element_ids):
        return CandidateVerification(
            candidate_id=candidate.candidate_id,
            status=GroundingStatus.REJECTED_INVALID_REFERENCE,
            grounding_score=0,
            detail="duplicate source reference",
        )
    if any(reference not in by_id for reference in candidate.source_element_ids):
        return CandidateVerification(
            candidate_id=candidate.candidate_id,
            status=GroundingStatus.REJECTED_INVALID_REFERENCE,
            grounding_score=0,
            detail="unknown source reference",
        )
    source = " ".join(
        (by_id[reference].reviewed_text or by_id[reference].text).strip()
        for reference in sorted(
            candidate.source_element_ids,
            key=lambda reference: by_id[reference].reading_order,
        )
    )
    proposed = _normalized(candidate.value)
    normalized_source = _normalized(source)
    if proposed == normalized_source:
        status = (
            GroundingStatus.GROUNDED
            if candidate.value == source
            else GroundingStatus.GROUNDED_WITH_NORMALIZATION
        )
        return CandidateVerification(
            candidate_id=candidate.candidate_id,
            status=status,
            grounding_score=1,
        )
    sensitive_source = _SENSITIVE.findall(normalized_source)
    sensitive_proposed = _SENSITIVE.findall(proposed)
    if sensitive_source != sensitive_proposed:
        return CandidateVerification(
            candidate_id=candidate.candidate_id,
            status=GroundingStatus.REJECTED_SENSITIVE_MISMATCH,
            grounding_score=0,
            detail="number, identifier, URL, email, unit, or negation changed",
        )
    source_tokens, proposed_tokens = _tokens(normalized_source), _tokens(proposed)
    score: float
    if not proposed_tokens:
        score = 0.0
    else:
        remaining = list(source_tokens)
        matched = 0
        for token in proposed_tokens:
            if token in remaining:
                remaining.remove(token)
                matched += 1
        score = matched / max(len(source_tokens), len(proposed_tokens), 1)
    if score >= 0.95 and all(token in source_tokens for token in proposed_tokens):
        status = GroundingStatus.GROUNDED_WITH_NORMALIZATION
    elif score >= 0.8:
        status = GroundingStatus.NEEDS_REVIEW
    else:
        status = GroundingStatus.REJECTED_UNGROUNDED
    return CandidateVerification(
        candidate_id=candidate.candidate_id,
        status=status,
        grounding_score=score,
        detail=None if status is GroundingStatus.GROUNDED_WITH_NORMALIZATION else "text is not fully supported by cited source",
    )


def merge_verified_candidates(
    candidates: list[SemanticCandidate],
    elements: list[ExtractedElement],
) -> SemanticResult:
    accepted = {
        GroundingStatus.GROUNDED,
        GroundingStatus.GROUNDED_WITH_NORMALIZATION,
    }
    claimed: set[str] = set()
    content: dict[str, Any] = {}
    verifications: list[CandidateVerification] = []
    coverage: dict[str, CoverageEntry] = {
        element.element_id: CoverageEntry(
            element_id=element.element_id,
            status="unclassified" if element.text.strip() else "ignored_non_text",
        )
        for element in elements
    }
    for candidate in sorted(candidates, key=lambda item: item.source_order):
        verification = verify_candidate(candidate, elements)
        if verification.status in accepted and claimed.intersection(
            candidate.source_element_ids
        ):
            verification = CandidateVerification(
                candidate_id=candidate.candidate_id,
                status=GroundingStatus.REJECTED_OVERLAP,
                grounding_score=verification.grounding_score,
                detail="source text was already consumed",
            )
        verifications.append(verification)
        if verification.status not in accepted:
            continue
        claimed.update(candidate.source_element_ids)
        current = content.get(candidate.key)
        content[candidate.key] = (
            candidate.value
            if current is None
            else [*current, candidate.value]
            if isinstance(current, list)
            else [current, candidate.value]
        )
        for reference in candidate.source_element_ids:
            coverage[reference] = CoverageEntry(
                element_id=reference,
                status="consumed",
                candidate_id=candidate.candidate_id,
            )
    remainder = [
        (element.reviewed_text or element.text).strip()
        for element in sorted(elements, key=lambda item: item.reading_order)
        if coverage[element.element_id].status == "unclassified"
        and (element.reviewed_text or element.text).strip()
    ]
    if remainder:
        content["unclassified"] = remainder
    mode: Literal["deterministic", "verified_ai", "hybrid"]
    mode = (
        "verified_ai"
        if candidates and not remainder
        else "hybrid"
        if candidates
        else "deterministic"
    )
    return SemanticResult(
        mode=mode,
        candidates=candidates,
        verifications=verifications,
        coverage=list(coverage.values()),
        final_content=content,
    )
