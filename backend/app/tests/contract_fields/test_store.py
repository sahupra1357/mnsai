"""Round-trip tests for the contract_field_extraction table.

Run against an in-memory SQLite engine so they need no Postgres. The fixture turns
`PRAGMA foreign_keys=ON`, so foreign keys **are** enforced for real here — a dangling
`owner_id` raises `IntegrityError` as it would on Postgres.

Still metadata-only, asserted from the DDL Alembic renders rather than executed:
`ondelete` CASCADE / SET NULL propagation (nothing here deletes a user), and the
server-side `DEFAULT ''` (every insert supplies all ten columns explicitly).
"""

import uuid
from collections.abc import Iterator
from typing import Any, cast

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.contract_fields.catalogue import (
    CANONICAL_FIELD_KEYS,
    DEFAULT_FIELD_KEYS,
    NON_DEFAULT_FIELD_KEYS,
)
from app.contract_fields.models import ExtractionStatus, VerificationAction
from app.contract_fields.store import (
    effective_fields,
    get_extraction,
    human_supplied_keys,
    insert_extraction,
    list_extractions,
    machine_fields,
    save_verification,
)
from app.models import ContractFieldExtractionRecord, User

# The mapped table object, untyped on the SQLModel class itself.
TABLE = cast(Any, ContractFieldExtractionRecord).__table__

OWNER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a1")
OTHER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000b2")
DOCUMENT_ID = uuid.UUID("00000000-0000-0000-0000-0000000000c3")

MACHINE_VALUES = {
    "contract_title": "Master Services Agreement",
    "parties": "Acme Corp; Northwind Ltd",
    "effective_date": "15/01/2026",
    "term_end_date": "14/01/2027",
    "contract_value": "USD 250000.00",
    "governing_law": "State of Delaware",
}


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # SQLite ignores foreign keys unless asked; switch them on so a dangling
    # owner_id fails here the way it fails on Postgres.
    @event.listens_for(engine, "connect")
    def _enforce_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(engine)
    with Session(engine) as active:
        active.add(
            User(id=OWNER_ID, email="owner@example.com", hashed_password="hashed")
        )
        active.add(
            User(id=OTHER_ID, email="other@example.com", hashed_password="hashed")
        )
        active.commit()
        yield active


def _insert(
    session: Session,
    *,
    owner_id: uuid.UUID = OWNER_ID,
    fields: dict[str, str] | None = None,
    selected: list[str] | None = None,
    status: ExtractionStatus = ExtractionStatus.COMPLETE,
    unresolved: list[dict[str, Any]] | None = None,
    source_name: str = "msa.pdf",
) -> ContractFieldExtractionRecord:
    return insert_extraction(
        session,
        owner_id=owner_id,
        document_id=DOCUMENT_ID,
        source_name=source_name,
        source_sha256="a" * 64,
        fields=MACHINE_VALUES if fields is None else fields,
        selected_fields=(
            [*DEFAULT_FIELD_KEYS, "governing_law"] if selected is None else selected
        ),
        extraction_status=status,
        unresolved_fields=unresolved or [],
        field_provenance=[
            {
                "field_key": "contract_title",
                "page_number": 1,
                "source_element_ids": ["element-1"],
                "grounding_status": "grounded",
                "confidence": 0.98,
            }
        ],
        warnings=["provider unavailable, deterministic extraction only"],
    )


def _verify(*args: Any, **kwargs: Any) -> ContractFieldExtractionRecord:
    """`save_verification` for a row that must exist — narrows away the 404 case."""

    record = save_verification(*args, **kwargs)
    assert record is not None
    return record


# --------------------------------------------------------------------------- #
# The table maps one-to-one onto the ten-key JSON
# --------------------------------------------------------------------------- #


def test_the_table_has_a_column_for_every_catalogue_key_in_order() -> None:
    columns = [column.name for column in TABLE.columns]
    field_columns = [name for name in columns if name in CANONICAL_FIELD_KEYS]

    assert tuple(field_columns) == CANONICAL_FIELD_KEYS
    assert ContractFieldExtractionRecord.__tablename__ == "contract_field_extraction"


def test_every_field_column_is_not_null_default_blank() -> None:
    for key in CANONICAL_FIELD_KEYS:
        column = TABLE.columns[key]
        assert column.nullable is False, key
        assert column.server_default is not None, key
        assert column.server_default.arg == "", key


def test_insert_then_read_round_trips_the_ten_keys(session: Session) -> None:
    record = _insert(session)
    stored = get_extraction(session, record.id, OWNER_ID)

    assert stored is not None
    values = machine_fields(stored)
    assert tuple(values) == CANONICAL_FIELD_KEYS
    assert len(values) == 10
    for key, expected in MACHINE_VALUES.items():
        assert values[key] == expected
    # Every column is a string; nothing came back NULL.
    assert all(isinstance(getattr(stored, key), str) for key in CANONICAL_FIELD_KEYS)


def test_a_field_that_was_never_requested_is_stored_blank(session: Session) -> None:
    record = _insert(
        session,
        fields={**MACHINE_VALUES, "termination_clause": "leaked value"},
        selected=["governing_law"],
    )

    # Not selected -> not persisted, however it arrived.
    assert record.termination_clause == ""
    # A formerly-fixed key is now legitimate; only junk and duplicates are dropped.
    assert record.selected_fields == ["governing_law"]
    # ...and the selection list is what distinguishes it from an extracted blank.
    assert record.notice_period == ""


def test_all_ten_fields_selected_round_trips(session: Session) -> None:
    filled = dict.fromkeys(CANONICAL_FIELD_KEYS, "value")
    record = _insert(session, fields=filled, selected=list(CANONICAL_FIELD_KEYS))

    assert machine_fields(record) == filled
    assert record.selected_fields == list(CANONICAL_FIELD_KEYS)


def test_a_needs_verification_row_is_persisted_like_any_other(
    session: Session,
) -> None:
    unresolved = [{"field_key": "term_end_date", "reason": "not_found", "detail": None}]
    record = _insert(
        session,
        fields={**MACHINE_VALUES, "term_end_date": ""},
        status=ExtractionStatus.NEEDS_VERIFICATION,
        unresolved=unresolved,
    )
    stored = get_extraction(session, record.id, OWNER_ID)

    assert stored is not None
    assert stored.extraction_status == "needs_verification"
    assert stored.unresolved_fields == unresolved
    assert stored.term_end_date == ""
    assert stored.warnings and stored.field_provenance


# --------------------------------------------------------------------------- #
# Owner scoping
# --------------------------------------------------------------------------- #


def test_another_owners_row_is_invisible(session: Session) -> None:
    record = _insert(session, owner_id=OTHER_ID)

    assert get_extraction(session, record.id, OWNER_ID) is None
    assert get_extraction(session, record.id, OTHER_ID) is not None


def test_records_are_listed_owner_scoped(session: Session) -> None:
    _insert(session, source_name="mine.pdf")
    _insert(session, owner_id=OTHER_ID, source_name="theirs.pdf")

    rows, total = list_extractions(session, OWNER_ID)

    assert total == 1
    assert [row.source_name for row in rows] == ["mine.pdf"]


def test_records_can_be_filtered_by_status(session: Session) -> None:
    _insert(session, source_name="complete.pdf")
    _insert(
        session,
        source_name="failed.pdf",
        fields={**MACHINE_VALUES, "term_end_date": ""},
        status=ExtractionStatus.NEEDS_VERIFICATION,
        unresolved=[{"field_key": "term_end_date", "reason": "not_found"}],
    )

    rows, total = list_extractions(
        session, OWNER_ID, extraction_status=ExtractionStatus.NEEDS_VERIFICATION
    )

    assert total == 1
    assert [row.source_name for row in rows] == ["failed.pdf"]
    assert list_extractions(session, OWNER_ID)[1] == 2


def test_paging_reports_the_unpaged_total(session: Session) -> None:
    for index in range(3):
        _insert(session, source_name=f"contract-{index}.pdf")

    rows, total = list_extractions(session, OWNER_ID, skip=1, limit=1)

    assert total == 3
    assert len(rows) == 1


# --------------------------------------------------------------------------- #
# Verification never overwrites the machine columns
# --------------------------------------------------------------------------- #


def test_a_human_value_never_overwrites_its_machine_column(session: Session) -> None:
    record = _insert(
        session,
        fields={**MACHINE_VALUES, "term_end_date": ""},
        status=ExtractionStatus.NEEDS_VERIFICATION,
        unresolved=[{"field_key": "term_end_date", "reason": "not_found"}],
    )

    updated = _verify(
        session,
        record.id,
        OWNER_ID,
        action=VerificationAction.APPROVE,
        status=ExtractionStatus.VERIFIED,
        values={"term_end_date": "14/01/2027"},
        actor_id=OWNER_ID,
        note="read off page 1",
    )

    # The machine column is untouched; the human value lives beside it.
    assert updated.term_end_date == ""
    assert updated.verified_values == {"term_end_date": "14/01/2027"}
    assert machine_fields(updated)["term_end_date"] == ""
    assert effective_fields(updated)["term_end_date"] == "14/01/2027"
    assert human_supplied_keys(updated) == ["term_end_date"]
    assert updated.extraction_status == "verified"
    assert updated.verified_by == OWNER_ID
    assert updated.verified_at is not None
    assert len(updated.audit_events) == 1
    assert updated.audit_events[0]["event_type"] == "contract_fields.approve"
    assert updated.audit_events[0]["details"]["note"] == "read off page 1"


def test_save_persists_partial_work_without_stamping_a_verifier(
    session: Session,
) -> None:
    record = _insert(
        session,
        fields={**MACHINE_VALUES, "term_end_date": "", "contract_value": ""},
        status=ExtractionStatus.NEEDS_VERIFICATION,
        unresolved=[
            {"field_key": "term_end_date", "reason": "not_found"},
            {"field_key": "contract_value", "reason": "normalization_failed"},
        ],
    )

    updated = _verify(
        session,
        record.id,
        OWNER_ID,
        action=VerificationAction.SAVE,
        status=ExtractionStatus.NEEDS_VERIFICATION,
        values={"term_end_date": "14/01/2027"},
        actor_id=OWNER_ID,
    )

    assert updated.extraction_status == "needs_verification"
    assert updated.verified_by is None
    assert updated.verified_at is None
    assert updated.verified_values == {"term_end_date": "14/01/2027"}


def test_audit_events_append_and_verified_values_merge(session: Session) -> None:
    record = _insert(
        session,
        fields={**MACHINE_VALUES, "term_end_date": "", "contract_value": ""},
        status=ExtractionStatus.NEEDS_VERIFICATION,
        unresolved=[
            {"field_key": "term_end_date", "reason": "not_found"},
            {"field_key": "contract_value", "reason": "normalization_failed"},
        ],
    )

    _verify(
        session,
        record.id,
        OWNER_ID,
        action=VerificationAction.SAVE,
        status=ExtractionStatus.NEEDS_VERIFICATION,
        values={"term_end_date": "14/01/2027"},
        actor_id=OWNER_ID,
    )
    updated = _verify(
        session,
        record.id,
        OWNER_ID,
        action=VerificationAction.APPROVE,
        status=ExtractionStatus.VERIFIED,
        values={"contract_value": "USD 250000.00"},
        actor_id=OWNER_ID,
    )

    assert updated.verified_values == {
        "term_end_date": "14/01/2027",
        "contract_value": "USD 250000.00",
    }
    assert [event["event_type"] for event in updated.audit_events] == [
        "contract_fields.save",
        "contract_fields.approve",
    ]
    assert sorted(human_supplied_keys(updated)) == ["contract_value", "term_end_date"]


def test_effective_fields_falls_back_to_the_machine_value(session: Session) -> None:
    record = _insert(session)

    values = effective_fields(record)

    assert tuple(values) == CANONICAL_FIELD_KEYS
    assert values["contract_title"] == "Master Services Agreement"
    assert human_supplied_keys(record) == []


# --------------------------------------------------------------------------- #
# A non-value never erases the machine value
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("supplied", ["   ", "", 12345, None])
def test_a_non_value_falls_back_to_the_machine_value(
    session: Session, supplied: object
) -> None:
    record = _insert(session)
    # Written straight to the column: whatever route or migration put it there,
    # the two helpers must still agree about it.
    record.verified_values = {"contract_title": supplied}  # type: ignore[dict-item]
    session.add(record)
    session.commit()

    assert effective_fields(record)["contract_title"] == "Master Services Agreement"
    assert human_supplied_keys(record) == []


def test_a_real_human_value_wins_over_the_machine_value(session: Session) -> None:
    record = _insert(session)
    updated = _verify(
        session,
        record.id,
        OWNER_ID,
        action=VerificationAction.SAVE,
        status=ExtractionStatus.NEEDS_VERIFICATION,
        values={"contract_title": "Amended Master Services Agreement"},
        actor_id=OWNER_ID,
    )

    assert effective_fields(updated)["contract_title"] == (
        "Amended Master Services Agreement"
    )
    assert human_supplied_keys(updated) == ["contract_title"]
    assert updated.contract_title == "Master Services Agreement"


# --------------------------------------------------------------------------- #
# The store cannot persist a state the response model forbids
# --------------------------------------------------------------------------- #


def test_verification_refuses_a_never_requested_key(session: Session) -> None:
    record = _insert(session, selected=[])

    with pytest.raises(ValueError, match="never requested"):
        save_verification(
            session,
            record.id,
            OWNER_ID,
            action=VerificationAction.SAVE,
            status=ExtractionStatus.NEEDS_VERIFICATION,
            values={"termination_clause": "HUMAN"},
            actor_id=OWNER_ID,
        )

    assert effective_fields(record)["termination_clause"] == ""


def test_verification_refuses_an_unknown_key(session: Session) -> None:
    record = _insert(session)

    with pytest.raises(ValueError, match="bogus_key"):
        save_verification(
            session,
            record.id,
            OWNER_ID,
            action=VerificationAction.SAVE,
            status=ExtractionStatus.NEEDS_VERIFICATION,
            values={"contract_title": "fine", "bogus_key": "X"},
            actor_id=OWNER_ID,
        )

    assert record.verified_values == {}


def test_verification_accepts_a_selected_optional_key(session: Session) -> None:
    record = _insert(session, selected=["governing_law"])

    updated = _verify(
        session,
        record.id,
        OWNER_ID,
        action=VerificationAction.SAVE,
        status=ExtractionStatus.NEEDS_VERIFICATION,
        values={"governing_law": "State of New York"},
        actor_id=OWNER_ID,
    )

    assert updated.verified_values == {"governing_law": "State of New York"}


def test_the_stored_selection_is_sanitized(session: Session) -> None:
    record = _insert(
        session,
        selected=["governing_law", "bogus", "contract_title", "governing_law"],
    )

    # Canonical order, de-duplicated, junk dropped. `contract_title` survives — it is
    # an ordinary selectable key now. This column is what tells a never-requested
    # blank from an extracted-and-not-found one.
    assert record.selected_fields == ["contract_title", "governing_law"]


# --------------------------------------------------------------------------- #
# A failed write leaves the session usable
# --------------------------------------------------------------------------- #


def test_a_failed_insert_leaves_the_session_usable(session: Session) -> None:
    _insert(session, source_name="good.pdf")

    with pytest.raises(IntegrityError):
        _insert(session, owner_id=uuid.uuid4(), source_name="orphan.pdf")

    # The request fails, but the handler can still touch the session afterwards.
    rows, total = list_extractions(session, OWNER_ID)
    assert total == 1
    assert [row.source_name for row in rows] == ["good.pdf"]


# --------------------------------------------------------------------------- #
# Zero optional fields selected — the case most likely to regress
# --------------------------------------------------------------------------- #


def test_insert_with_only_the_default_five_selected_round_trips(
    session: Session,
) -> None:
    record = _insert(session, fields=MACHINE_VALUES, selected=list(DEFAULT_FIELD_KEYS))
    stored = get_extraction(session, record.id, OWNER_ID)

    assert stored is not None
    values = machine_fields(stored)
    assert tuple(values) == CANONICAL_FIELD_KEYS
    assert len(values) == 10
    assert stored.selected_fields == list(DEFAULT_FIELD_KEYS)
    # The five fixed fields are always requested and always written...
    for key in DEFAULT_FIELD_KEYS:
        assert values[key] == MACHINE_VALUES[key]
    # ...and all five optional keys are present and blank, including the one the
    # extractor did find, because it was never requested.
    for key in NON_DEFAULT_FIELD_KEYS:
        assert values[key] == ""


# --------------------------------------------------------------------------- #
# The store never writes a row that cannot be read back
# --------------------------------------------------------------------------- #


def test_insert_refuses_complete_with_a_blank_requested_field(
    session: Session,
) -> None:
    # `ContractFieldResult.validate_contract` would raise on this row, so
    # GET /{id} and GET /records would 500 on it permanently.
    with pytest.raises(ValueError, match="cannot store `complete`"):
        _insert(session, fields={**MACHINE_VALUES, "term_end_date": ""})


def test_insert_refuses_complete_when_a_selected_optional_is_blank(
    session: Session,
) -> None:
    with pytest.raises(ValueError, match="notice_period"):
        _insert(session, selected=["governing_law", "notice_period"])


def test_insert_refuses_needs_verification_with_no_unresolved_fields(
    session: Session,
) -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        _insert(
            session,
            fields={**MACHINE_VALUES, "term_end_date": ""},
            status=ExtractionStatus.NEEDS_VERIFICATION,
            unresolved=[],
        )


def test_verification_refuses_to_verify_a_still_blank_field(session: Session) -> None:
    record = _insert(
        session,
        fields={**MACHINE_VALUES, "term_end_date": "", "contract_value": ""},
        status=ExtractionStatus.NEEDS_VERIFICATION,
        unresolved=[
            {"field_key": "term_end_date", "reason": "not_found"},
            {"field_key": "contract_value", "reason": "normalization_failed"},
        ],
    )

    # Only one of the two blanks was filled in.
    with pytest.raises(ValueError, match="contract_value"):
        save_verification(
            session,
            record.id,
            OWNER_ID,
            action=VerificationAction.APPROVE,
            status=ExtractionStatus.VERIFIED,
            values={"term_end_date": "14/01/2027"},
            actor_id=OWNER_ID,
        )

    assert record.extraction_status == "needs_verification"


def test_verification_refuses_a_non_string_value(session: Session) -> None:
    record = _insert(session)

    with pytest.raises(ValueError, match="not strings"):
        save_verification(
            session,
            record.id,
            OWNER_ID,
            action=VerificationAction.SAVE,
            status=ExtractionStatus.NEEDS_VERIFICATION,
            values={"contract_title": 12345},  # type: ignore[dict-item]
            actor_id=OWNER_ID,
        )

    assert record.verified_values == {}


def test_verification_of_another_owners_record_is_a_miss(session: Session) -> None:
    record = _insert(session, owner_id=OTHER_ID)

    outcome = save_verification(
        session,
        record.id,
        OWNER_ID,
        action=VerificationAction.SAVE,
        status=ExtractionStatus.NEEDS_VERIFICATION,
        values={"contract_title": "hijacked"},
        actor_id=OWNER_ID,
    )

    # Structural 404: the store looks the row up itself and finds nothing.
    assert outcome is None
    assert record.verified_values == {}
