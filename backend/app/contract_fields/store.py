"""Persistence for contract field extractions.

The ten field columns of ``contract_field_extraction`` map one-to-one onto the ten
catalogue keys — the module-level check below fails at import if they ever drift, so
a renamed key cannot silently stop being written.

The columns hold the **machine** output and are never overwritten by a human:
verification writes to ``verified_values``, and the *effective* value of a field is
its verified value when present, otherwise its machine value.

Every read is owner-scoped. There is no unscoped read in this module by design.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, cast

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import ContractFieldExtractionRecord
from app.visual_document_extractor.models import AuditEvent

from .catalogue import (
    CANONICAL_FIELD_KEYS,
    assemble_fields,
    requested_field_keys,
)
from .models import ExtractionStatus, VerificationAction

_COLUMNS = cast(Any, ContractFieldExtractionRecord).__table__.c

_missing = [key for key in CANONICAL_FIELD_KEYS if key not in _COLUMNS]
if _missing:
    raise RuntimeError(
        "contract_field_extraction is missing a column for every catalogue key: "
        + ", ".join(_missing)
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _commit(session: Session) -> None:
    """Commit, rolling back on failure so the session stays usable.

    A failed write must fail the request — but it must not leave the caller holding
    a session that raises `PendingRollbackError` on its next statement.
    """

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise


def machine_fields(record: ContractFieldExtractionRecord) -> dict[str, str]:
    """The ten machine-extracted values, in catalogue order — the JSON contract."""

    return assemble_fields({key: getattr(record, key) for key in CANONICAL_FIELD_KEYS})


def _human_value(record: ContractFieldExtractionRecord, key: str) -> str:
    """The human-supplied value for `key`, or ``""`` when there is not one.

    The single predicate for "a human filled this in": a non-string, a blank, or
    whitespace is **not** a value. `effective_fields` and `human_supplied_keys` both
    go through here, so they can never disagree about a given cell — a disagreement
    would render a blank that is neither the machine value nor flagged as human.
    """

    value = (record.verified_values or {}).get(key)
    return value if isinstance(value, str) and value.strip() else ""


def effective_fields(record: ContractFieldExtractionRecord) -> dict[str, str]:
    """The ten values as a human sees them: verified where present, else machine.

    A non-value in `verified_values` falls back to the machine value rather than
    erasing it.
    """

    machine = machine_fields(record)
    return assemble_fields(
        {
            key: (_human_value(record, key) or machine[key])
            for key in CANONICAL_FIELD_KEYS
        }
    )


def human_supplied_keys(record: ContractFieldExtractionRecord) -> list[str]:
    """Which fields a human filled in, so the table can mark those cells."""

    return [key for key in CANONICAL_FIELD_KEYS if _human_value(record, key)]


def insert_extraction(
    session: Session,
    *,
    owner_id: uuid.UUID,
    document_id: uuid.UUID,
    source_name: str,
    source_sha256: str,
    fields: Mapping[str, str],
    selected_fields: Sequence[str],
    extraction_status: ExtractionStatus,
    unresolved_fields: Sequence[Mapping[str, Any]] = (),
    field_provenance: Sequence[Mapping[str, Any]] = (),
    warnings: Sequence[str] = (),
) -> ContractFieldExtractionRecord:
    """Write one row. The ten columns come from the assembled ten-key payload, so a
    key that was never requested is stored as ``""`` rather than omitted.

    A `needs_verification` result is persisted like any other — the row is exactly
    what the human works from.
    """

    # Sanitize once and use the result for both the columns and the stored
    # selection: this column is the only thing that tells a never-requested blank
    # from an extracted-and-not-found blank, so an unknown, duplicated, or
    # fixed-key entry in it would silently break the failure rule downstream.
    requested = requested_field_keys(selected_fields)
    selected = [key for key in CANONICAL_FIELD_KEYS if key in set(requested)]
    values = assemble_fields(fields, requested_keys=requested)

    # The same argument that guards the keys guards the status: a row whose status
    # contradicts its values raises in `ContractFieldResult.validate_contract`, so
    # `GET /{id}` and `GET /records` would 500 on it *permanently* — worse than the
    # 422 the key check prevents. Refuse to write it.
    blank_requested = [key for key in requested if not values[key]]
    if extraction_status is ExtractionStatus.COMPLETE and blank_requested:
        raise ValueError(
            "cannot store `complete` while these requested fields are blank: "
            + ", ".join(blank_requested)
        )
    if (
        extraction_status is ExtractionStatus.NEEDS_VERIFICATION
        and not unresolved_fields
    ):
        raise ValueError(
            "`needs_verification` means at least one requested field is blank, so "
            "unresolved_fields cannot be empty"
        )

    record = ContractFieldExtractionRecord(
        owner_id=owner_id,
        document_id=document_id,
        source_name=source_name,
        source_sha256=source_sha256,
        selected_fields=selected,
        extraction_status=extraction_status.value,
        unresolved_fields=[dict(entry) for entry in unresolved_fields],
        field_provenance=[dict(entry) for entry in field_provenance],
        warnings=list(warnings),
        verified_values={},
        audit_events=[],
        created_at=_utc_now(),
        **values,
    )
    session.add(record)
    _commit(session)
    session.refresh(record)
    return record


def get_extraction(
    session: Session, extraction_id: uuid.UUID, owner_id: uuid.UUID
) -> ContractFieldExtractionRecord | None:
    """One row, owner-scoped. Another owner's row reads as absent, not forbidden."""

    return session.exec(
        select(ContractFieldExtractionRecord).where(
            ContractFieldExtractionRecord.id == extraction_id,
            ContractFieldExtractionRecord.owner_id == owner_id,
        )
    ).first()


def list_extractions(
    session: Session,
    owner_id: uuid.UUID,
    *,
    extraction_status: ExtractionStatus | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[ContractFieldExtractionRecord], int]:
    """One owner-scoped page, newest first, optionally filtered by status.

    Ordered by `created_at`, never by a date column: those hold DD/MM/YYYY text and
    would sort lexically.
    """

    filters = [ContractFieldExtractionRecord.owner_id == owner_id]
    if extraction_status is not None:
        filters.append(
            ContractFieldExtractionRecord.extraction_status == extraction_status.value
        )
    total = session.exec(
        select(func.count()).select_from(ContractFieldExtractionRecord).where(*filters)
    ).one()
    rows = session.exec(
        select(ContractFieldExtractionRecord)
        .where(*filters)
        .order_by(_COLUMNS.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return list(rows), int(total)


def save_verification(
    session: Session,
    extraction_id: uuid.UUID,
    owner_id: uuid.UUID,
    *,
    action: VerificationAction,
    status: ExtractionStatus,
    values: Mapping[str, str],
    actor_id: uuid.UUID | None,
    note: str | None = None,
) -> ContractFieldExtractionRecord | None:
    """Persist one verification action.

    Human input is merged into ``verified_values``; **the ten machine columns are
    never touched**. Whether an *approve* is permitted is decided before this call
    (that is `verification.py`'s job in Phase 3); the store records the outcome and
    appends the audit event.

    Which **keys** may be written is enforced here, not deferred: `values` accepts
    requested keys only — exactly the fields this row actually
    selected. A never-requested or unknown key raises `ValueError`, which the route
    turns into a 422. Without this the store could persist a state its own response
    model forbids ("was not selected, so its value must be blank").
    """

    # Owner scoping is structural: this function cannot be handed another owner's
    # row, because it looks the row up itself. A miss is a 404, not a write.
    record = get_extraction(session, extraction_id, owner_id)
    if record is None:
        return None

    requested = requested_field_keys(record.selected_fields or [])
    rejected: list[str] = []
    not_strings: list[str] = []
    for key, value in values.items():
        if key not in requested:
            rejected.append(key)
        elif not isinstance(value, str):
            not_strings.append(key)
    if rejected:
        raise ValueError(
            "these keys were never requested for this extraction and cannot be "
            "verified: " + ", ".join(sorted(rejected))
        )
    if not_strings:
        # Every field value is a string. Storing an int here reads back as
        # "Input should be a valid string".
        raise ValueError(
            "these verified values are not strings: " + ", ".join(sorted(not_strings))
        )

    merged = dict(record.verified_values or {})
    merged.update(values)

    # ...and the status invariant: a human cannot approve a result that is still
    # incomplete, so `verified` requires every unresolved key to have a non-blank
    # effective value once this action is applied.
    if status is ExtractionStatus.VERIFIED:
        still_blank: list[str] = []
        for entry in record.unresolved_fields or []:
            entry_key = entry.get("field_key") if isinstance(entry, dict) else None
            if not isinstance(entry_key, str) or entry_key not in CANONICAL_FIELD_KEYS:
                continue
            human = merged.get(entry_key)
            if (isinstance(human, str) and human.strip()) or getattr(
                record, entry_key, ""
            ):
                continue
            still_blank.append(entry_key)
        if still_blank:
            raise ValueError(
                "cannot verify while these fields are still blank: "
                + ", ".join(still_blank)
            )

    record.verified_values = merged
    record.extraction_status = status.value

    stamped = _utc_now()
    if action in (VerificationAction.APPROVE, VerificationAction.REJECT):
        record.verified_by = actor_id
        record.verified_at = stamped

    event = AuditEvent(
        event_type=f"contract_fields.{action.value}",
        actor_id=actor_id,
        details={
            "status": status.value,
            "fields": sorted(values),
            **({"note": note} if note else {}),
        },
    )
    record.audit_events = [
        *(record.audit_events or []),
        event.model_dump(mode="json"),
    ]
    session.add(record)
    _commit(session)
    session.refresh(record)
    return record
