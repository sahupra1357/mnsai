"""Request and response shapes for contract field extraction.

Types only — the runtime that fills them in (extractor, grounding, verification,
store, service) lands in later phases. What lives here is the *contract*:

* the JSON payload always carries the ten catalogue keys, in catalogue order, all
  strings (``ContractFields``);
* the operator may select only optional keys (``FieldSelection``);
* a blank in a **requested** field — exactly the fields the operator selected
  selected — is a failure that forces ``needs_verification``, while a blank in an
  unselected optional field is expected and must never trigger it
  (``ExtractionStatus``, ``UnresolvedField``, and the invariants on
  ``ContractFieldResult``).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.visual_document_extractor.models import AuditEvent, utc_now
from app.visual_document_extractor.semantic import GroundingStatus

from .catalogue import (
    CANONICAL_FIELD_KEYS,
    DEFAULT_FIELD_KEYS,
    FIELD_CATALOGUE,
    FieldDefinition,
    assemble_fields,
    requested_field_keys,
)

__all__ = [
    "ContractFieldRecordRow",
    "ContractFieldResult",
    "ContractFieldsPage",
    "ContractFields",
    "ExtractionStatus",
    "FieldCatalogueResponse",
    "FieldProvenance",
    "FieldSelection",
    "UnresolvedField",
    "UnresolvedReason",
    "VerificationAction",
    "VerificationOutcome",
    "VerificationRequest",
]


class ExtractionStatus(str, Enum):
    """Outcome of one field extraction.

    Mirrors the existing pipeline's review vocabulary (``PageStatus`` /
    ``ReviewStatus``) rather than inventing a parallel one.
    """

    #: Every requested field came back non-blank. No human action needed.
    COMPLETE = "complete"
    #: At least one requested field is blank. The failure state — one is enough.
    NEEDS_VERIFICATION = "needs_verification"
    #: A human supplied or confirmed the unresolved fields and approved the record.
    VERIFIED = "verified"
    #: A human judged the extraction unusable.
    REJECTED = "rejected"


class UnresolvedReason(str, Enum):
    """Why a requested field came back blank. Never a generic "failed"."""

    #: No candidate for the field was found in the extracted elements.
    NOT_FOUND = "not_found"
    #: A candidate existed but could not be grounded in a source element.
    UNGROUNDED = "ungrounded"
    #: A grounded candidate could not be normalized to the field's value format.
    NORMALIZATION_FAILED = "normalization_failed"
    #: The LLM provider was unavailable, so deterministic extraction found nothing.
    PROVIDER_UNAVAILABLE = "provider_unavailable"


class VerificationAction(str, Enum):
    SAVE = "save"
    APPROVE = "approve"
    REJECT = "reject"


class UnresolvedField(BaseModel):
    """One requested field that came back blank, with the reason it did."""

    model_config = ConfigDict(frozen=True)

    field_key: str
    reason: UnresolvedReason
    #: The raw text that could not be normalized, when there was one. Never a guess.
    detail: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_key(self) -> UnresolvedField:
        if self.field_key not in CANONICAL_FIELD_KEYS:
            raise ValueError(f"unknown contract field key: {self.field_key}")
        return self


class FieldProvenance(BaseModel):
    """Where a non-blank value came from. Blank values carry no provenance."""

    model_config = ConfigDict(frozen=True)

    field_key: str
    page_number: int = Field(ge=1)
    source_element_ids: list[str] = Field(min_length=1)
    grounding_status: GroundingStatus
    confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_key(self) -> FieldProvenance:
        if self.field_key not in CANONICAL_FIELD_KEYS:
            raise ValueError(f"unknown contract field key: {self.field_key}")
        return self


class FieldSelection(BaseModel):
    """The operator's choice: any subset of the ten fields, from one up to all ten.

    Every field is selectable and every field is deselectable — there is no field
    that is always extracted. What is refused is an **empty** selection (there would
    be nothing to extract), an unknown key, or a duplicate.

    Five fields are *default-selected* in the UI, which is a starting point only: a
    selection that omits all five of them is valid and is extracted as asked.
    """

    # `validate_assignment` refuses an empty, unknown, or duplicated selection however
    # it arrives — post-construction assignment included. It raises *after* writing
    # the value, though, so `frozen` joins it: the assignment is refused and the
    # instance is left clean even if the caller swallows the error.
    model_config = ConfigDict(frozen=True, validate_assignment=True)

    selected_fields: list[str]

    @model_validator(mode="before")
    @classmethod
    def canonicalize_selection(cls, data: Any) -> Any:
        """Reorder a *valid* selection into catalogue order, so the persisted list
        is stable and comparable. An invalid selection is left exactly as given for
        `validate_selection` to reject — reordering must never launder it."""

        if not isinstance(data, dict):
            return data
        selected = data.get("selected_fields")
        if not isinstance(selected, list) or not all(
            isinstance(key, str) for key in selected
        ):
            return data
        if len(set(selected)) != len(selected) or any(
            key not in CANONICAL_FIELD_KEYS for key in selected
        ):
            return data
        chosen = set(selected)
        return {
            **data,
            "selected_fields": [key for key in CANONICAL_FIELD_KEYS if key in chosen],
        }

    @model_validator(mode="after")
    def validate_selection(self) -> FieldSelection:
        if not self.selected_fields:
            raise ValueError(
                "select at least one contract field: an empty selection has "
                "nothing to extract"
            )
        seen: set[str] = set()
        for key in self.selected_fields:
            if key not in CANONICAL_FIELD_KEYS:
                raise ValueError(f"unknown contract field key: {key}")
            if key in seen:
                raise ValueError(f"duplicate contract field key: {key}")
            seen.add(key)
        return self

    @property
    def requested_keys(self) -> tuple[str, ...]:
        """Exactly what was selected — the failure scope, nothing added implicitly."""

        return requested_field_keys(self.selected_fields)


class ContractFields(BaseModel):
    """The ten-key JSON contract.

    One explicit string field per catalogue key, declared in catalogue order, so the
    serialized payload always has the same ten keys in the same order — for every
    selection, including none-selected and all-selected. A field that was not
    selected, not found, or not groundable is ``""``: never ``None``, never absent,
    never an invented value.

    The ten names here mirror the ten table columns one-to-one; the module-level
    consistency check below fails at import if they ever drift from the catalogue.
    """

    # `extra="forbid"`: the key set is static, so an eleventh key is a defect, not
    # something to silently drop.
    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_title: str = ""
    parties: str = ""
    effective_date: str = ""
    term_end_date: str = ""
    contract_value: str = ""
    governing_law: str = ""
    payment_terms: str = ""
    notice_period: str = ""
    renewal_terms: str = ""
    termination_clause: str = ""

    @classmethod
    def from_values(
        cls,
        values: Mapping[str, object] | None = None,
        *,
        requested_keys: Iterable[str] | None = None,
    ) -> ContractFields:
        """Assemble the ten keys from a partial mapping of extracted values."""

        return cls(**assemble_fields(values, requested_keys=requested_keys))

    def as_dict(self) -> dict[str, str]:
        """The ten keys, in catalogue order, every value a string."""

        return assemble_fields(self.model_dump())

    def blank_keys(self) -> tuple[str, ...]:
        """Every key whose value is blank, requested or not, in catalogue order."""

        values = self.as_dict()
        return tuple(key for key in CANONICAL_FIELD_KEYS if not values[key])


if tuple(ContractFields.model_fields) != CANONICAL_FIELD_KEYS:
    raise RuntimeError(
        "ContractFields no longer matches the catalogue: the JSON contract, the "
        "catalogue, and the table columns must stay one-to-one"
    )


class FieldCatalogueResponse(BaseModel):
    """``GET /fields`` — the schema, served so the frontend never hardcodes a copy."""

    fields: list[FieldDefinition] = Field(default_factory=lambda: list(FIELD_CATALOGUE))
    #: The keys the picker starts with in its selected list. A starting point only —
    #: the client may submit any non-empty subset of `fields`.
    default_fields: list[str] = Field(default_factory=lambda: list(DEFAULT_FIELD_KEYS))


class ContractFieldResult(BaseModel):
    """The response for one extraction: the ten keys plus everything around them.

    The right-hand JSON pane renders ``fields`` only. A ``needs_verification``
    result is a business outcome, not a transport error — it is persisted and
    returned with HTTP 200 like any other, because the row is what the human works
    from.
    """

    # Every invariant below must hold however the state is reached.
    # `validate_assignment` re-runs `validate_contract` when a field is assigned, so
    # flipping `extraction_status` to `verified` cannot sneak past it; `frozen` then
    # keeps the instance clean, since pydantic writes the value before the validator
    # raises. A changed result is a new result.
    model_config = ConfigDict(frozen=True, validate_assignment=True)

    extraction_id: uuid.UUID
    document_id: uuid.UUID
    fields: ContractFields
    #: Which optional keys were requested — so a blank that was never asked for is
    #: distinguishable from one that was extracted and not found.
    selected_fields: list[str] = Field(default_factory=list)
    extraction_status: ExtractionStatus
    unresolved_fields: list[UnresolvedField] = Field(default_factory=list)
    field_provenance: list[FieldProvenance] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    #: Human-supplied values, kept separate from the machine-extracted ``fields``,
    #: which are never overwritten. The effective value is the verified one if
    #: present, otherwise the machine one.
    verified_values: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    @property
    def requested_keys(self) -> tuple[str, ...]:
        return requested_field_keys(self.selected_fields)

    @model_validator(mode="after")
    def validate_contract(self) -> ContractFieldResult:
        if not self.selected_fields:
            raise ValueError("a result must record at least one selected field")
        for key in self.selected_fields:
            if key not in CANONICAL_FIELD_KEYS:
                raise ValueError(f"unknown contract field key: {key}")
        if len(set(self.selected_fields)) != len(self.selected_fields):
            raise ValueError("duplicate contract field key")

        requested = set(self.requested_keys)
        values = self.fields.as_dict()

        # An unselected field is out of scope: it is always blank, and a value must
        # never leak into it. This now covers all ten keys, not just the optional
        # half — any of the ten can be left out of a selection.
        for key in CANONICAL_FIELD_KEYS:
            if key not in requested and values[key]:
                raise ValueError(f"{key} was not selected, so its value must be blank")

        # The failure rule, encoded: unresolved keys are requested keys that are
        # blank, and any unresolved key means the result is not `complete`.
        for unresolved in self.unresolved_fields:
            if unresolved.field_key not in requested:
                raise ValueError(
                    f"{unresolved.field_key} was never requested, so it cannot be "
                    "unresolved"
                )
            # An unresolved field is a field that came back blank. A key holding a
            # machine value is resolved, whatever reason is attached to it.
            if values[unresolved.field_key]:
                raise ValueError(
                    f"{unresolved.field_key} holds a machine value, so it cannot be "
                    "listed as unresolved"
                )
        if (
            self.extraction_status is ExtractionStatus.NEEDS_VERIFICATION
            and not self.unresolved_fields
        ):
            raise ValueError(
                "needs_verification means at least one requested field is blank, so "
                "unresolved_fields cannot be empty"
            )
        if (
            self.unresolved_fields
            and self.extraction_status is ExtractionStatus.COMPLETE
        ):
            raise ValueError(
                "an extraction with unresolved requested fields is never complete"
            )

        # ...and the other half: a blank requested field is a failure, so it must be
        # listed. Without this, a classifier could return a blank requested field with
        # an empty `unresolved_fields` and status `complete` — the silent pass this
        # whole feature exists to prevent. A key a human has filled in is not blank.
        unresolved_keys = {entry.field_key for entry in self.unresolved_fields}
        for key in self.requested_keys:
            if values[key] or self.verified_values.get(key, "").strip():
                continue
            if key not in unresolved_keys:
                raise ValueError(
                    f"{key} was requested and is blank, so it must be listed in "
                    "unresolved_fields"
                )

        # A human cannot approve a result that is still incomplete. Once the status
        # is `verified`, every unresolved key must have a non-blank *effective*
        # value — the human's if present, otherwise the machine's. Phase 3's route
        # check then refuses a state that is already unrepresentable here.
        if self.extraction_status is ExtractionStatus.VERIFIED:
            still_blank = [
                entry.field_key
                for entry in self.unresolved_fields
                if not (
                    self.verified_values.get(entry.field_key, "").strip()
                    or values[entry.field_key].strip()
                )
            ]
            if still_blank:
                raise ValueError(
                    "cannot be verified while these fields are still blank: "
                    + ", ".join(still_blank)
                )

        # Human corrections may only touch requested keys.
        for key in self.verified_values:
            if key not in requested:
                raise ValueError(f"{key} was never requested, so it cannot be verified")
        return self


class ContractFieldRecordRow(BaseModel):
    """One row of the persisted table view.

    Carries both halves so the table can show the **effective** value and still mark
    which cells a human supplied: ``fields`` is the untouched machine output and
    ``verified_values`` the human overlay.
    """

    extraction_id: uuid.UUID
    document_id: uuid.UUID
    source_name: str
    fields: ContractFields
    selected_fields: list[str] = Field(default_factory=list)
    extraction_status: ExtractionStatus
    unresolved_fields: list[UnresolvedField] = Field(default_factory=list)
    verified_values: dict[str, str] = Field(default_factory=dict)
    verified_by: uuid.UUID | None = None
    verified_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ContractFieldsPage(BaseModel):
    """``GET /records`` — one owner-scoped page of rows, matching house convention."""

    data: list[ContractFieldRecordRow] = Field(default_factory=list)
    count: int = Field(default=0, ge=0)


class VerificationRequest(BaseModel):
    """``PATCH /{extraction_id}/verify`` — mirrors ``PageReviewRequest``.

    ``values`` accepts requested keys only; an unknown key, or one that was never
    requested, is a 422. ``approve`` is refused while any unresolved field still has
    a blank effective value — a human cannot approve an incomplete result.
    """

    action: Literal["save", "approve", "reject"]
    values: dict[str, str] = Field(default_factory=dict)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_values(self) -> VerificationRequest:
        for key in self.values:
            if key not in CANONICAL_FIELD_KEYS:
                raise ValueError(f"unknown contract field key: {key}")
        return self


class VerificationOutcome(BaseModel):
    """The audited result of a verification action."""

    result: ContractFieldResult
    verified_by: uuid.UUID | None = None
    verified_at: datetime | None = None
    audit_events: list[AuditEvent] = Field(default_factory=list)
