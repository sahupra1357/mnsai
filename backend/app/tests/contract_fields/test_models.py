"""The JSON contract, the selection rules, and the failure rule, as types."""

import json
import uuid

import pytest
from pydantic import ValidationError

from app.contract_fields.catalogue import (
    CANONICAL_FIELD_KEYS,
    DEFAULT_FIELD_KEYS,
    NON_DEFAULT_FIELD_KEYS,
)
from app.contract_fields.models import (
    ContractFieldResult,
    ContractFields,
    ExtractionStatus,
    FieldProvenance,
    FieldSelection,
    UnresolvedField,
    UnresolvedReason,
    VerificationRequest,
)
from app.visual_document_extractor.semantic import GroundingStatus

MACHINE_VALUES = {
    "contract_title": "Master Services Agreement",
    "parties": "Acme Corp; Northwind Ltd",
    "effective_date": "15/01/2026",
    "term_end_date": "14/01/2027",
    "contract_value": "USD 250000.00",
}


def _result(**overrides: object) -> ContractFieldResult:
    payload: dict[str, object] = {
        "extraction_id": uuid.uuid4(),
        "document_id": uuid.uuid4(),
        "fields": ContractFields.from_values(MACHINE_VALUES),
        "selected_fields": list(DEFAULT_FIELD_KEYS),
        "extraction_status": ExtractionStatus.COMPLETE,
    }
    payload.update(overrides)
    return ContractFieldResult(**payload)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# The ten-key JSON contract
# --------------------------------------------------------------------------- #


def test_contract_fields_mirrors_the_catalogue_one_to_one() -> None:
    assert tuple(ContractFields.model_fields) == CANONICAL_FIELD_KEYS


def test_contract_fields_serializes_the_same_ten_keys_in_order() -> None:
    for selected in (["governing_law"], list(NON_DEFAULT_FIELD_KEYS), []):
        fields = ContractFields.from_values(
            MACHINE_VALUES, requested_keys=[*DEFAULT_FIELD_KEYS, *selected]
        )
        dumped = json.loads(fields.model_dump_json())

        assert tuple(dumped) == CANONICAL_FIELD_KEYS
        assert tuple(fields.as_dict()) == CANONICAL_FIELD_KEYS
        assert all(isinstance(value, str) for value in dumped.values())


def test_contract_fields_defaults_every_key_to_blank() -> None:
    fields = ContractFields()

    assert fields.as_dict() == dict.fromkeys(CANONICAL_FIELD_KEYS, "")
    assert fields.blank_keys() == CANONICAL_FIELD_KEYS


def test_contract_fields_rejects_a_key_outside_the_catalogue() -> None:
    with pytest.raises(ValidationError):
        ContractFields(not_a_field="x")  # type: ignore[call-arg]


def test_contract_fields_blank_keys_reports_what_is_missing() -> None:
    fields = ContractFields.from_values(MACHINE_VALUES)

    assert fields.blank_keys() == NON_DEFAULT_FIELD_KEYS


# --------------------------------------------------------------------------- #
# FieldSelection — only the five optional keys are selectable
# --------------------------------------------------------------------------- #


def test_selection_accepts_one_field_through_all_ten() -> None:
    """Any non-empty subset of the ten, and the scope is exactly the subset."""

    assert FieldSelection(selected_fields=["parties"]).requested_keys == ("parties",)
    assert (
        FieldSelection(selected_fields=list(DEFAULT_FIELD_KEYS)).requested_keys
        == DEFAULT_FIELD_KEYS
    )
    assert (
        FieldSelection(selected_fields=list(NON_DEFAULT_FIELD_KEYS)).requested_keys
        == NON_DEFAULT_FIELD_KEYS
    )
    assert (
        FieldSelection(selected_fields=list(CANONICAL_FIELD_KEYS)).requested_keys
        == CANONICAL_FIELD_KEYS
    )


def test_selection_rejects_an_empty_selection() -> None:
    """Nothing selected means nothing to extract — refused, not silently defaulted."""

    with pytest.raises(ValidationError):
        FieldSelection(selected_fields=[])
    with pytest.raises(ValidationError):
        FieldSelection()


def test_selection_is_stored_in_canonical_order() -> None:
    selection = FieldSelection(selected_fields=["payment_terms", "governing_law"])

    assert selection.selected_fields == ["governing_law", "payment_terms"]


def test_selection_rejects_an_unknown_key() -> None:
    with pytest.raises(ValidationError, match="unknown contract field key"):
        FieldSelection(selected_fields=["not_a_field"])


def test_selection_rejects_a_duplicate_key() -> None:
    with pytest.raises(ValidationError, match="duplicate contract field key"):
        FieldSelection(selected_fields=["governing_law", "governing_law"])


def test_a_formerly_fixed_key_is_an_ordinary_selection() -> None:
    """`contract_title` was un-selectable; it is now a key like any other."""

    selection = FieldSelection(selected_fields=["contract_title"])

    assert selection.selected_fields == ["contract_title"]
    assert selection.requested_keys == ("contract_title",)


# --------------------------------------------------------------------------- #
# The failure rule
# --------------------------------------------------------------------------- #


def test_all_requested_fields_present_is_complete() -> None:
    result = _result()

    assert result.extraction_status is ExtractionStatus.COMPLETE
    assert result.unresolved_fields == []
    assert result.requested_keys == DEFAULT_FIELD_KEYS


def test_a_blank_unselected_optional_field_does_not_make_it_a_failure() -> None:
    # governing_law was selected and found; the other four optional fields were never
    # requested, so their blanks are expected and change nothing.
    result = _result(
        fields=ContractFields.from_values(
            {**MACHINE_VALUES, "governing_law": "State of Delaware"}
        ),
        selected_fields=[*DEFAULT_FIELD_KEYS, "governing_law"],
    )

    assert result.fields.governing_law == "State of Delaware"
    assert result.fields.notice_period == ""
    assert result.extraction_status is ExtractionStatus.COMPLETE


def test_a_blank_requested_field_cannot_be_silently_complete() -> None:
    # The silent pass this feature exists to prevent: a requested field is blank, yet
    # nothing lists it and the status claims success.
    with pytest.raises(ValidationError, match="must be listed in unresolved_fields"):
        _result(fields=ContractFields.from_values({**MACHINE_VALUES, "parties": ""}))

    with pytest.raises(ValidationError, match="must be listed in unresolved_fields"):
        _result(
            fields=ContractFields.from_values(
                {**MACHINE_VALUES, "governing_law": ""},
                requested_keys=[*DEFAULT_FIELD_KEYS, "governing_law"],
            ),
            selected_fields=[*DEFAULT_FIELD_KEYS, "governing_law"],
        )


def test_a_human_filled_key_is_not_forced_into_unresolved_fields() -> None:
    result = _result(
        fields=ContractFields.from_values({**MACHINE_VALUES, "term_end_date": ""}),
        extraction_status=ExtractionStatus.VERIFIED,
        verified_values={"term_end_date": "14/01/2027"},
    )

    assert result.unresolved_fields == []
    assert result.fields.term_end_date == ""


def test_unresolved_fields_cannot_be_complete() -> None:
    with pytest.raises(ValidationError, match="never complete"):
        _result(
            fields=ContractFields.from_values({**MACHINE_VALUES, "term_end_date": ""}),
            unresolved_fields=[
                UnresolvedField(
                    field_key="term_end_date", reason=UnresolvedReason.NOT_FOUND
                )
            ],
        )


def test_a_blank_requested_field_is_carried_as_needs_verification() -> None:
    result = _result(
        fields=ContractFields.from_values({**MACHINE_VALUES, "term_end_date": ""}),
        selected_fields=[*DEFAULT_FIELD_KEYS, "notice_period"],
        extraction_status=ExtractionStatus.NEEDS_VERIFICATION,
        unresolved_fields=[
            UnresolvedField(
                field_key="term_end_date",
                reason=UnresolvedReason.NORMALIZATION_FAILED,
                detail="three years from the Effective Date",
            ),
            UnresolvedField(
                field_key="notice_period", reason=UnresolvedReason.NOT_FOUND
            ),
        ],
    )

    assert result.extraction_status is ExtractionStatus.NEEDS_VERIFICATION
    assert [entry.field_key for entry in result.unresolved_fields] == [
        "term_end_date",
        "notice_period",
    ]
    # Still a full ten-key payload — a failure is never a withheld result.
    assert tuple(result.fields.as_dict()) == CANONICAL_FIELD_KEYS


def test_an_unrequested_field_cannot_be_unresolved() -> None:
    with pytest.raises(ValidationError, match="never requested"):
        _result(
            extraction_status=ExtractionStatus.NEEDS_VERIFICATION,
            unresolved_fields=[
                UnresolvedField(
                    field_key="renewal_terms", reason=UnresolvedReason.NOT_FOUND
                )
            ],
        )


def test_an_unselected_optional_field_can_never_carry_a_value() -> None:
    with pytest.raises(ValidationError, match="must be blank"):
        _result(
            fields=ContractFields.from_values(
                {**MACHINE_VALUES, "termination_clause": "leaked"}
            )
        )


def test_verified_values_are_limited_to_requested_keys() -> None:
    with pytest.raises(ValidationError, match="cannot be verified"):
        _result(
            extraction_status=ExtractionStatus.VERIFIED,
            verified_values={"payment_terms": "Net 30"},
        )

    result = _result(
        fields=ContractFields.from_values({**MACHINE_VALUES, "term_end_date": ""}),
        extraction_status=ExtractionStatus.VERIFIED,
        unresolved_fields=[
            UnresolvedField(
                field_key="term_end_date", reason=UnresolvedReason.NOT_FOUND
            )
        ],
        verified_values={"term_end_date": "14/01/2027"},
    )

    # The human value never overwrites the machine column.
    assert result.fields.term_end_date == ""
    assert result.verified_values["term_end_date"] == "14/01/2027"


def test_verified_is_unrepresentable_while_an_unresolved_field_is_blank() -> None:
    # "A human cannot approve a result that is still incomplete" is an invariant,
    # not merely a route check.
    for verified_values in ({}, {"term_end_date": "   "}):
        with pytest.raises(ValidationError, match="still blank"):
            _result(
                fields=ContractFields.from_values(
                    {**MACHINE_VALUES, "term_end_date": ""}
                ),
                extraction_status=ExtractionStatus.VERIFIED,
                unresolved_fields=[
                    UnresolvedField(
                        field_key="term_end_date", reason=UnresolvedReason.NOT_FOUND
                    )
                ],
                verified_values=verified_values,
            )


def test_an_unresolved_field_must_actually_be_blank() -> None:
    with pytest.raises(ValidationError, match="holds a machine value"):
        _result(
            extraction_status=ExtractionStatus.NEEDS_VERIFICATION,
            unresolved_fields=[
                UnresolvedField(
                    field_key="term_end_date", reason=UnresolvedReason.NOT_FOUND
                )
            ],
        )


def test_needs_verification_requires_at_least_one_unresolved_field() -> None:
    with pytest.raises(ValidationError, match="cannot be empty"):
        _result(extraction_status=ExtractionStatus.NEEDS_VERIFICATION)


def test_the_invariants_survive_post_construction_assignment() -> None:
    result = _result(
        fields=ContractFields.from_values({**MACHINE_VALUES, "term_end_date": ""}),
        extraction_status=ExtractionStatus.NEEDS_VERIFICATION,
        unresolved_fields=[
            UnresolvedField(
                field_key="term_end_date", reason=UnresolvedReason.NOT_FOUND
            )
        ],
    )

    # Flipping the status without filling the blank must not be reachable by
    # mutation either, and the refused assignment must not leave the instance dirty.
    with pytest.raises(ValidationError):
        result.extraction_status = ExtractionStatus.VERIFIED
    assert result.extraction_status is ExtractionStatus.NEEDS_VERIFICATION
    assert '"extraction_status":"verified"' not in result.model_dump_json()


def test_selection_rejects_a_bad_post_construction_assignment() -> None:
    selection = FieldSelection(selected_fields=["governing_law"])

    for bad in (["contract_title"], ["nope"], ["payment_terms", "payment_terms"]):
        with pytest.raises(ValidationError):
            selection.selected_fields = bad
    assert selection.selected_fields == ["governing_law"]


def test_unresolved_reasons_are_specific_never_generic() -> None:
    assert {reason.value for reason in UnresolvedReason} == {
        "not_found",
        "ungrounded",
        "normalization_failed",
        "provider_unavailable",
    }


def test_extraction_status_vocabulary() -> None:
    assert [status.value for status in ExtractionStatus] == [
        "complete",
        "needs_verification",
        "verified",
        "rejected",
    ]


# --------------------------------------------------------------------------- #
# Provenance and verification requests
# --------------------------------------------------------------------------- #


def test_provenance_records_where_a_value_came_from() -> None:
    provenance = FieldProvenance(
        field_key="contract_title",
        page_number=1,
        source_element_ids=["element-1"],
        grounding_status=GroundingStatus.GROUNDED,
        confidence=0.98,
    )

    assert provenance.field_key == "contract_title"
    assert provenance.grounding_status is GroundingStatus.GROUNDED


def test_provenance_rejects_an_unknown_field_and_an_empty_source() -> None:
    with pytest.raises(ValidationError):
        FieldProvenance(
            field_key="not_a_field",
            page_number=1,
            source_element_ids=["element-1"],
            grounding_status=GroundingStatus.GROUNDED,
        )
    with pytest.raises(ValidationError):
        FieldProvenance(
            field_key="parties",
            page_number=1,
            source_element_ids=[],
            grounding_status=GroundingStatus.GROUNDED,
        )


def test_verification_request_mirrors_the_page_review_shape() -> None:
    request = VerificationRequest(
        action="approve", values={"term_end_date": "14/01/2027"}, note="checked page 1"
    )

    assert request.action == "approve"
    assert request.values == {"term_end_date": "14/01/2027"}


def test_verification_request_rejects_an_unknown_key_and_action() -> None:
    with pytest.raises(ValidationError, match="unknown contract field key"):
        VerificationRequest(action="save", values={"not_a_field": "x"})
    with pytest.raises(ValidationError):
        VerificationRequest(action="delete")  # type: ignore[arg-type]
