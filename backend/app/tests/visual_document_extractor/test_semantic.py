from app.visual_document_extractor.models import ExtractedElement
from app.visual_document_extractor.semantic import (
    GroundingStatus,
    SemanticCandidate,
    merge_verified_candidates,
    verify_candidate,
)


def _elements() -> list[ExtractedElement]:
    return [
        ExtractedElement(
            element_id="one",
            text="Total $52.40",
            reading_order=0,
        ),
        ExtractedElement(
            element_id="two",
            text="Contact a@example.com",
            reading_order=1,
        ),
        ExtractedElement(
            element_id="three",
            text="Unclassified source text",
            reading_order=2,
        ),
    ]


def test_grounding_rejects_changed_sensitive_value() -> None:
    verification = verify_candidate(
        SemanticCandidate(
            candidate_id="total",
            key="total",
            value="Total $52.90",
            source_element_ids=["one"],
            source_order=0,
        ),
        _elements(),
    )

    assert verification.status is GroundingStatus.REJECTED_SENSITIVE_MISMATCH


def test_grounding_rejects_unknown_reference() -> None:
    verification = verify_candidate(
        SemanticCandidate(
            candidate_id="invented",
            key="summary",
            value="Invented",
            source_element_ids=["missing"],
            source_order=0,
        ),
        _elements(),
    )

    assert verification.status is GroundingStatus.REJECTED_INVALID_REFERENCE


def test_verified_merge_keeps_unclaimed_source_exactly_once() -> None:
    result = merge_verified_candidates(
        [
            SemanticCandidate(
                candidate_id="contact",
                key="contact",
                value="Contact a@example.com",
                source_element_ids=["two"],
                source_order=1,
            )
        ],
        _elements(),
    )

    assert result.mode == "hybrid"
    assert result.final_content == {
        "contact": "Contact a@example.com",
        "unclassified": ["Total $52.40", "Unclassified source text"],
    }
    assert [entry.status for entry in result.coverage] == [
        "unclassified",
        "consumed",
        "unclassified",
    ]
