"""Extraction, grounding, and outcome classification.

These are the tests for the rule the whole feature turns on: a blank in a
**requested** field is a failure; a blank in an **unselected** optional field is not.
"""

import uuid
from typing import Any

import pytest

from app.contract_fields.catalogue import DEFAULT_FIELD_KEYS
from app.contract_fields.extractor import (
    PROVIDER_UNAVAILABLE_WARNING,
    extract_deterministic,
    propose_candidates,
    split_parties,
)
from app.contract_fields.grounding import ground_value
from app.contract_fields.models import (
    ExtractionStatus,
    UnresolvedReason,
    VerificationAction,
)
from app.contract_fields.service import resolve_fields
from app.contract_fields.verification import classify_outcome, next_status
from app.visual_document_extractor.models import (
    DocumentResult,
    ExtractedElement,
    PageResult,
    SourceMetadata,
)
from app.visual_document_extractor.semantic import GroundingStatus

OWNER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a1")

CONTRACT_LINES = [
    ("heading", "Master Services Agreement"),
    (
        "paragraph",
        "This Agreement is made by and between Acme Corp, Inc. and Northwind Ltd.",
    ),
    ("paragraph", "Effective Date: 15 January 2026"),
    ("paragraph", "Expiration Date: 14 January 2027"),
    ("paragraph", "Total contract value: USD 250,000.00"),
    ("paragraph", "Governing Law: State of Delaware"),
    ("paragraph", "Payment Terms: Net 30 days from invoice date"),
]


def _document(lines: list[tuple[str, str]] | None = None) -> DocumentResult:
    rows = CONTRACT_LINES if lines is None else lines
    elements = [
        ExtractedElement(
            element_id=f"e{index}",
            type=kind,  # type: ignore[arg-type]
            text=text,
            reading_order=index,
        )
        for index, (kind, text) in enumerate(rows)
    ]
    return DocumentResult(
        owner_id=OWNER_ID,
        source=SourceMetadata(
            source_name="msa.pdf",
            source_sha256="a" * 64,
            media_type="application/pdf",
            size_bytes=1024,
            page_count=1,
        ),
        pages=[PageResult(page_number=1, elements=elements)],
    )


def _resolve(
    selected: list[str], lines: list[tuple[str, str]] | None = None
) -> tuple[dict[str, str], ExtractionStatus, list[Any], Any]:
    from app.contract_fields.catalogue import requested_field_keys

    document = _document(lines)
    requested = requested_field_keys(selected)
    proposals = propose_candidates(document, list(requested), use_provider=False)
    outcome = resolve_fields(document, requested, proposals)
    from app.contract_fields.catalogue import assemble_fields

    fields = assemble_fields(outcome.values, requested_keys=requested)
    status, unresolved = classify_outcome(fields, selected, outcome.reasons)
    return fields, status, unresolved, outcome


# --------------------------------------------------------------------------- #
# Deterministic extraction
# --------------------------------------------------------------------------- #


def test_deterministic_extraction_finds_the_default_fields() -> None:
    fields, status, unresolved, _ = _resolve(list(DEFAULT_FIELD_KEYS))

    assert fields["contract_title"] == "Master Services Agreement"
    assert fields["parties"] == "Acme Corp, Inc.; Northwind Ltd."
    assert fields["effective_date"] == "15/01/2026"
    assert fields["term_end_date"] == "14/01/2027"
    assert fields["contract_value"] == "USD 250000.00"
    assert status is ExtractionStatus.COMPLETE
    assert unresolved == []


def test_a_selected_optional_field_is_extracted() -> None:
    fields, status, _, _ = _resolve(
        [*DEFAULT_FIELD_KEYS, "governing_law", "payment_terms"]
    )

    assert fields["governing_law"] == "State of Delaware"
    assert fields["payment_terms"] == "Net 30 days from invoice date"
    assert status is ExtractionStatus.COMPLETE


def test_the_payload_always_carries_all_ten_keys() -> None:
    from app.contract_fields.catalogue import (
        CANONICAL_FIELD_KEYS,
        NON_DEFAULT_FIELD_KEYS,
    )

    for selected in (
        ["governing_law"],
        list(DEFAULT_FIELD_KEYS),
        list(NON_DEFAULT_FIELD_KEYS),
        list(CANONICAL_FIELD_KEYS),
    ):
        fields, _, _, _ = _resolve(list(selected))
        assert tuple(fields) == CANONICAL_FIELD_KEYS
        assert all(isinstance(value, str) for value in fields.values())


# --------------------------------------------------------------------------- #
# The failure rule
# --------------------------------------------------------------------------- #


def test_a_blank_unselected_optional_field_stays_complete() -> None:
    # governing_law IS in the document, but was not selected: not extracted, blank,
    # and emphatically not a failure.
    fields, status, unresolved, _ = _resolve(list(DEFAULT_FIELD_KEYS))

    assert fields["governing_law"] == ""
    assert fields["termination_clause"] == ""
    assert status is ExtractionStatus.COMPLETE
    assert unresolved == []


def test_a_blank_selected_optional_field_is_a_failure() -> None:
    fields, status, unresolved, _ = _resolve([*DEFAULT_FIELD_KEYS, "notice_period"])

    assert fields["notice_period"] == ""
    assert status is ExtractionStatus.NEEDS_VERIFICATION
    assert [entry.field_key for entry in unresolved] == ["notice_period"]
    assert unresolved[0].reason is UnresolvedReason.NOT_FOUND


def test_a_blank_fixed_field_is_a_failure() -> None:
    lines = [row for row in CONTRACT_LINES if "Expiration" not in row[1]]
    fields, status, unresolved, _ = _resolve(list(DEFAULT_FIELD_KEYS), lines)

    assert fields["term_end_date"] == ""
    assert status is ExtractionStatus.NEEDS_VERIFICATION
    assert [entry.field_key for entry in unresolved] == ["term_end_date"]


def test_one_blank_is_enough_no_partial_credit() -> None:
    lines = [row for row in CONTRACT_LINES if "Expiration" not in row[1]]
    _, status, unresolved, _ = _resolve([*DEFAULT_FIELD_KEYS, "governing_law"], lines)

    # Nine of ten resolved is still needs_verification.
    assert status is ExtractionStatus.NEEDS_VERIFICATION
    assert len(unresolved) == 1


def test_an_unnormalizable_date_is_blank_with_a_specific_reason() -> None:
    lines = [
        row
        if "Effective" not in row[1]
        else ("paragraph", "Effective Date: 01/02/2026")
        for row in CONTRACT_LINES
    ]
    fields, status, unresolved, outcome = _resolve(list(DEFAULT_FIELD_KEYS), lines)

    assert fields["effective_date"] == ""
    assert status is ExtractionStatus.NEEDS_VERIFICATION
    reasons = {entry.field_key: entry.reason for entry in unresolved}
    assert reasons["effective_date"] is UnresolvedReason.NORMALIZATION_FAILED
    # The warning names the raw text rather than a generic failure.
    assert any("01/02/2026" in warning for warning in outcome.warnings)


def test_reasons_are_never_generic() -> None:
    _, _, unresolved, _ = _resolve([*DEFAULT_FIELD_KEYS, "notice_period"])

    assert all(
        entry.reason
        in {
            UnresolvedReason.NOT_FOUND,
            UnresolvedReason.UNGROUNDED,
            UnresolvedReason.NORMALIZATION_FAILED,
            UnresolvedReason.PROVIDER_UNAVAILABLE,
        }
        for entry in unresolved
    )


# --------------------------------------------------------------------------- #
# Grounding
# --------------------------------------------------------------------------- #


def test_an_ungrounded_value_is_blanked() -> None:
    elements = _document().pages[0].elements
    verdict = ground_value("governing_law", "State of New York", ["e5"], elements)

    assert verdict.accepted is False
    assert verdict.value == ""


def test_a_true_excerpt_is_grounded() -> None:
    elements = _document().pages[0].elements
    verdict = ground_value(
        "payment_terms", "Net 30 days from invoice date", ["e6"], elements
    )

    assert verdict.accepted is True


def test_a_dropped_negation_is_rejected() -> None:
    elements = [
        ExtractedElement(
            element_id="n1",
            text="This Agreement is not governed by the laws of Delaware",
            reading_order=0,
        )
    ]
    verdict = ground_value(
        "governing_law", "governed by the laws of Delaware", ["n1"], elements
    )

    assert verdict.accepted is False


def _element(element_id: str, text: str, order: int = 0) -> ExtractedElement:
    return ExtractedElement(element_id=element_id, text=text, reading_order=order)


# --------------------------------------------------------------------------- #
# What the loosened "appears in" gate must still refuse.
#
# Each of these was accepted by an earlier, weaker gate and reached the JSON and the
# persisted row as `complete` with no warning. They are the price of admitting an
# excerpt path at all, so they are pinned.
# --------------------------------------------------------------------------- #


def test_a_recital_date_is_not_the_term_end_date() -> None:
    # The clause carrying the date says nothing about a termination date; the label
    # three clauses earlier does not license it.
    elements = [
        _element(
            "r1",
            "The termination date is set out in Schedule 1, which the parties "
            "agreed on 3 March 2019.",
        )
    ]

    verdict = ground_value("term_end_date", "3 March 2019", ["r1"], elements)

    assert verdict.accepted is False
    assert verdict.value == ""


def test_an_unrelated_figure_is_not_the_contract_value() -> None:
    # Share capital is not consideration — and the element goes on to say the Buyer
    # pays nothing at all.
    elements = [
        _element(
            "c1",
            "The Supplier has share capital of USD 5,000,000. The Buyer shall pay "
            "nothing under this Agreement.",
        )
    ]

    verdict = ground_value("contract_value", "USD 5,000,000", ["c1"], elements)

    assert verdict.accepted is False


def test_a_value_spliced_across_two_elements_is_rejected() -> None:
    # "at least one source element" means one: this value is in neither.
    elements = [
        _element("s1", "The setup charge is USD 40,000 per", 0),
        _element("s2", "month plus expenses billed quarterly.", 1),
    ]

    verdict = ground_value(
        "payment_terms", "USD 40,000 per month", ["s1", "s2"], elements
    )

    assert verdict.accepted is False


def test_dropping_one_of_two_negations_is_rejected() -> None:
    # Keeping one "not" must not cover for dropping another: the value asserts
    # renewal where the source forbids it.
    elements = [
        _element(
            "n2", "The Term shall not renew. The Notice shall not be less than 30 days."
        )
    ]

    verdict = ground_value(
        "renewal_terms",
        "renew. The Notice shall not be less than 30 days",
        ["n2"],
        elements,
    )

    assert verdict.accepted is False


def test_a_carve_out_phrase_counts_as_a_negation() -> None:
    elements = [
        _element(
            "g1",
            "The parties agree to apply Delaware law other than the laws of the "
            "State of New York",
        )
    ]

    verdict = ground_value(
        "governing_law", "the laws of the State of New York", ["g1"], elements
    )

    assert verdict.accepted is False


CARVE_OUTS = [
    "other than for cause",
    "save for wilful default",
    "save that notice is given",
    "provided that notice is given",
    "subject to clause 9",
    "unless a party objects",
]


@pytest.mark.parametrize("carve_out", CARVE_OUTS)
@pytest.mark.parametrize("separator", [" ", ", "])
def test_a_carve_out_is_caught_with_or_without_a_comma(
    carve_out: str, separator: str
) -> None:
    # The comma form is how carve-outs are actually written, and it is the form a
    # clause-scoped guard cannot see: the carve-out lands in a clause the span does
    # not touch. One comma must never flip the verdict.
    elements = [
        _element(
            "co",
            f"Termination: The Agreement terminates on notice{separator}{carve_out}.",
        )
    ]

    verdict = ground_value(
        "termination_clause", "The Agreement terminates on notice", ["co"], elements
    )

    assert verdict.accepted is False


def test_a_conditioned_renewal_is_not_reported_as_unconditional() -> None:
    elements = [
        _element(
            "rn",
            "Renewal Terms: The Agreement renews annually, unless a party objects.",
        )
    ]

    verdict = ground_value(
        "renewal_terms", "The Agreement renews annually", ["rn"], elements
    )

    assert verdict.accepted is False


def test_a_sensitive_mismatch_is_never_overridden() -> None:
    # `verify_candidate` rejects a changed number outright; the excerpt path must
    # not rescue it.
    elements = [_element("m1", "Total contract value: USD 250,000.00")]

    verdict = ground_value("contract_value", "USD 250,900.00", ["m1"], elements)

    assert verdict.accepted is False
    assert verdict.status is GroundingStatus.REJECTED_SENSITIVE_MISMATCH


def test_a_bare_label_is_not_a_value() -> None:
    verdict = ground_value(
        "governing_law",
        "Governing Law",
        ["l1"],
        [_element("l1", "Governing Law: State of Delaware")],
    )
    assert verdict.accepted is False

    # ...including when the cited element *is* the heading, which gate 1 would
    # otherwise accept as an exact whole-element match with score 1.0.
    heading_only = ground_value(
        "governing_law", "Governing Law", ["l2"], [_element("l2", "Governing Law")]
    )
    assert heading_only.accepted is False
    assert heading_only.value == ""


@pytest.mark.parametrize(
    ("field_key", "value", "text"),
    [
        # These are *value* shapes that also appear in the extractor's search
        # patterns; treating them as labels blanked the canonical answer.
        ("payment_terms", "Net 30", "Payment Terms: Net 30"),
        (
            "notice_period",
            "90 days' prior written notice",
            "Notice Period: 90 days' prior written notice",
        ),
        ("renewal_terms", "Automatic renewal", "Renewal Terms: Automatic renewal"),
    ],
)
def test_the_label_screen_does_not_blank_the_canonical_value(
    field_key: str, value: str, text: str
) -> None:
    verdict = ground_value(field_key, value, ["v1"], [_element("v1", text)])

    assert verdict.accepted is True
    assert verdict.value == value


def test_an_accepted_excerpt_keeps_the_documents_own_casing() -> None:
    elements = [_element("k1", "governing law: state of delaware")]

    verdict = ground_value("governing_law", "STATE OF DELAWARE", ["k1"], elements)

    assert verdict.accepted is True
    assert verdict.value == "state of delaware"


def test_an_excerpt_acceptance_is_visible_in_the_provenance() -> None:
    elements = [_element("p1", "Payment Terms: Net 30 days from invoice date")]

    verdict = ground_value(
        "payment_terms", "Net 30 days from invoice date", ["p1"], elements
    )

    assert verdict.accepted is True
    # Not dressed up as a clean pass: a reviewer can see which values took the
    # weaker path, and the real grounding score is preserved.
    assert verdict.status is GroundingStatus.NEEDS_REVIEW
    assert verdict.score < 1.0
    assert verdict.detail == "verbatim excerpt of the cited source"


def test_a_labelled_date_and_amount_still_ground() -> None:
    # The fence must not blank the ordinary case.
    assert ground_value(
        "effective_date",
        "15 January 2026",
        ["d1"],
        [_element("d1", "Effective Date: 15 January 2026")],
    ).accepted
    assert ground_value(
        "contract_value",
        "USD 250,000.00",
        ["v1"],
        [_element("v1", "Total contract value: USD 250,000.00")],
    ).accepted


def test_an_unknown_element_reference_is_rejected() -> None:
    elements = _document().pages[0].elements
    verdict = ground_value("governing_law", "State of Delaware", ["nope"], elements)

    assert verdict.accepted is False


# --------------------------------------------------------------------------- #
# Parties — delimiting is the extractor's job
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("preamble", "expected"),
    [
        ("Acme Corp and Northwind Ltd", ["Acme Corp", "Northwind Ltd"]),
        ("Acme Corp, Inc. and Northwind Ltd.", ["Acme Corp, Inc.", "Northwind Ltd."]),
        # Not two parties: "Johnson" is not an entity name on its own.
        ("Johnson and Johnson", ["Johnson and Johnson"]),
        ("Smith and Wesson", ["Smith and Wesson"]),
    ],
)
def test_split_parties_only_splits_when_corroborated(
    preamble: str, expected: list[str]
) -> None:
    assert split_parties(preamble) == expected


def test_parties_are_grounded_individually() -> None:
    fields, _, _, _ = _resolve(list(DEFAULT_FIELD_KEYS))

    # Both names appear in the source element, so both survive grounding.
    assert fields["parties"] == "Acme Corp, Inc.; Northwind Ltd."


# --------------------------------------------------------------------------- #
# Provider degradation
# --------------------------------------------------------------------------- #


def test_a_missing_provider_degrades_instead_of_failing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.contract_fields.extractor as extractor

    def _boom(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise RuntimeError("401 Unauthorized")

    monkeypatch.setattr(extractor, "extract_with_provider", _boom)
    document = _document([("paragraph", "An unremarkable page with no fields.")])

    proposals = propose_candidates(
        document, ["contract_title", "parties", "effective_date"], use_provider=True
    )

    assert proposals.provider_available is False
    assert PROVIDER_UNAVAILABLE_WARNING in proposals.warnings


def test_provider_unavailable_becomes_a_specific_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.contract_fields.extractor as extractor
    from app.contract_fields.catalogue import requested_field_keys

    monkeypatch.setattr(
        extractor,
        "extract_with_provider",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("401")),
    )
    document = _document([("paragraph", "Nothing useful here.")])
    requested = requested_field_keys(DEFAULT_FIELD_KEYS)
    proposals = propose_candidates(document, list(requested), use_provider=True)
    outcome = resolve_fields(document, requested, proposals)

    assert outcome.reasons["effective_date"] is UnresolvedReason.PROVIDER_UNAVAILABLE


def test_the_deterministic_pass_needs_no_provider() -> None:
    candidates = extract_deterministic(_document(), ["contract_title", "parties"])

    assert set(candidates) == {"contract_title", "parties"}


# --------------------------------------------------------------------------- #
# Status transitions
# --------------------------------------------------------------------------- #


def test_status_transitions() -> None:
    assert next_status(VerificationAction.SAVE) is ExtractionStatus.NEEDS_VERIFICATION
    assert next_status(VerificationAction.APPROVE) is ExtractionStatus.VERIFIED
    assert next_status(VerificationAction.REJECT) is ExtractionStatus.REJECTED
