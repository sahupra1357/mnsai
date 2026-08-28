"""The failure rule, the unresolved reasons, and the status transitions.

One idea decides everything here:

> **Requested = exactly the fields the operator selected** — any subset of the ten,
> from one field to all ten, with nothing added implicitly. A blank in a requested
> field is a **failure**. A blank in an unselected field is expected and is not.

Getting that distinction wrong is the single most likely defect in this feature, so
it lives in exactly one function — `classify_outcome` — and everything else calls it.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence

from app.models import ContractFieldExtractionRecord
from app.visual_document_extractor.models import AuditEvent

from .catalogue import CANONICAL_FIELD_KEYS, requested_field_keys
from .models import (
    ExtractionStatus,
    UnresolvedField,
    UnresolvedReason,
    VerificationAction,
)


def requested_keys(selected_fields: Iterable[str] | None) -> tuple[str, ...]:
    """The keys the operator asked for. Blank in one of these is a failure."""

    return requested_field_keys(selected_fields)


def classify_outcome(
    fields: Mapping[str, str],
    selected_fields: Sequence[str],
    reasons: Mapping[str, UnresolvedReason] | None = None,
) -> tuple[ExtractionStatus, list[UnresolvedField]]:
    """Decide the outcome of one extraction.

    Every requested key that came back blank is unresolved, carrying the reason the
    step that produced the blank recorded — never a generic "failed". One unresolved
    key is enough: there is no partial-credit threshold.

    An unselected optional field is out of scope. It is blank, and that is correct,
    and it must never appear here.
    """

    reason_by_key = dict(reasons or {})
    unresolved = [
        UnresolvedField(
            field_key=key,
            reason=reason_by_key.get(key, UnresolvedReason.NOT_FOUND),
        )
        for key in requested_keys(selected_fields)
        if not fields.get(key, "").strip()
    ]
    status = (
        ExtractionStatus.NEEDS_VERIFICATION if unresolved else ExtractionStatus.COMPLETE
    )
    return status, unresolved


def effective_value(record: ContractFieldExtractionRecord, key: str) -> str:
    """A field as a human sees it: the verified value if there is one, else the
    machine value. A non-string or whitespace-only entry is not a value."""

    human = (record.verified_values or {}).get(key)
    if isinstance(human, str) and human.strip():
        return human
    machine = getattr(record, key, "")
    return machine if isinstance(machine, str) else ""


def unresolved_keys(record: ContractFieldExtractionRecord) -> list[str]:
    """The keys this row recorded as unresolved, in catalogue order."""

    listed = {
        entry.get("field_key")
        for entry in (record.unresolved_fields or [])
        if isinstance(entry, dict)
    }
    return [key for key in CANONICAL_FIELD_KEYS if key in listed]


def approval_blockers(
    record: ContractFieldExtractionRecord, values: Mapping[str, str]
) -> list[str]:
    """Unresolved keys that would still be blank after applying `values`.

    A human cannot approve a result that is still incomplete; the route turns a
    non-empty list into a 422 naming exactly these keys.
    """

    blockers = []
    for key in unresolved_keys(record):
        supplied = values.get(key)
        if isinstance(supplied, str) and supplied.strip():
            continue
        if effective_value(record, key).strip():
            continue
        blockers.append(key)
    return blockers


def next_status(action: VerificationAction) -> ExtractionStatus:
    """`save` leaves the failure standing; `approve` clears it; `reject` kills it."""

    if action is VerificationAction.APPROVE:
        return ExtractionStatus.VERIFIED
    if action is VerificationAction.REJECT:
        return ExtractionStatus.REJECTED
    return ExtractionStatus.NEEDS_VERIFICATION


def verification_event(
    action: VerificationAction,
    actor_id: uuid.UUID | None,
    keys: Sequence[str],
    note: str | None = None,
) -> AuditEvent:
    """One audit entry, following the existing `AuditEvent` shape."""

    return AuditEvent(
        event_type=f"contract_fields.{action.value}",
        actor_id=actor_id,
        details={
            "fields": sorted(keys),
            **({"note": note} if note else {}),
        },
    )
