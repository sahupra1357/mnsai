"""The `/api/v1/contract-extractions` endpoints, end to end.

The document extraction itself is stubbed — this feature never runs OCR, and the
existing pipeline is exercised by its own suite. What is tested here is everything
this feature adds: the schema endpoint, selection validation, the ten-key response,
the failure rule surfacing as 200 + `needs_verification`, owner scoping, and the
verification rules.
"""

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api.deps import get_current_user, get_db
from app.contract_fields.catalogue import CANONICAL_FIELD_KEYS, DEFAULT_FIELD_KEYS
from app.contract_fields.service import ContractFieldService
from app.main import app
from app.models import User
from app.visual_document_extractor.models import (
    DocumentResult,
    ExtractedElement,
    PageResult,
    SourceMetadata,
)

OWNER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a1")
OTHER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000b2")


def _user(user_id: uuid.UUID, email: str) -> User:
    return User(id=user_id, email=email, hashed_password="hashed", is_active=True)


FULL_CONTRACT = [
    ("heading", "Master Services Agreement"),
    (
        "paragraph",
        "This Agreement is made by and between Acme Corp, Inc. and Northwind Ltd.",
    ),
    ("paragraph", "Effective Date: 15 January 2026"),
    ("paragraph", "Expiration Date: 14 January 2027"),
    ("paragraph", "Total contract value: USD 250,000.00"),
    ("paragraph", "Governing Law: State of Delaware"),
]
INCOMPLETE_CONTRACT = [row for row in FULL_CONTRACT if "Expiration" not in row[1]]

# Every one of the ten fields, plainly labelled — the deterministic happy path.
TEN_FIELD_CONTRACT = FULL_CONTRACT + [
    ("paragraph", "Payment Terms: Net 30"),
    ("paragraph", "Notice Period: 90 days' prior written notice"),
    ("paragraph", "Renewal Terms: Automatic renewal"),
    ("paragraph", "Termination: Termination for convenience on notice"),
]

SOURCE_BYTES = b"%PDF-1.4 fake"


class _FakeExtractionService:
    """Stands in for the existing pipeline: returns a canned DocumentResult."""

    def __init__(self, lines: list[tuple[str, str]]) -> None:
        self.lines = lines

    def ingest(
        self, *, owner_id: uuid.UUID, source_name: str, content: bytes
    ) -> DocumentResult:
        elements = [
            ExtractedElement(
                element_id=f"e{index}",
                type=kind,  # type: ignore[arg-type]
                text=text,
                reading_order=index,
            )
            for index, (kind, text) in enumerate(self.lines)
        ]
        return DocumentResult(
            owner_id=owner_id,
            source=SourceMetadata(
                source_name=source_name,
                source_sha256="a" * 64,
                media_type="application/pdf",
                size_bytes=max(len(content), 1),
                page_count=1,
            ),
            pages=[PageResult(page_number=1, elements=elements)],
        )

    def get_source(
        self, document_id: uuid.UUID, owner_id: uuid.UUID
    ) -> tuple[bytes, str, str]:
        return SOURCE_BYTES, "application/pdf", "msa.pdf"


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as active:
        active.add(_user(OWNER_ID, "owner@example.com"))
        active.add(_user(OTHER_ID, "other@example.com"))
        active.commit()
        yield active


@pytest.fixture
def client(session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    import app.api.routes.contract_extractions as routes
    import app.contract_fields.extractor as extractor

    # Hermetic: the route defaults to `use_provider=True`, so without this every
    # upload in this module made a live, billable OpenAI call and the assertions
    # depended on what the model happened to return that run.
    monkeypatch.setattr(extractor, "extract_with_provider", lambda *_a, **_k: {})

    def _use(lines: list[tuple[str, str]]) -> None:
        monkeypatch.setattr(
            routes,
            "get_service",
            lambda: ContractFieldService(_FakeExtractionService(lines)),  # type: ignore[arg-type]
        )

    _use(FULL_CONTRACT)
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: _user(
        OWNER_ID, "owner@example.com"
    )
    with TestClient(app) as active:
        active.use_document = _use  # type: ignore[attr-defined]
        yield active
    app.dependency_overrides.clear()


def _upload(client: TestClient, selected: list[str] | None = None) -> Any:
    """Upload with an explicit selection.

    Defaults to the five default-selected keys — the scope these tests assumed back
    when those five were extracted implicitly. Pass `[]` to exercise the empty
    selection, which is now a 422.
    """

    chosen = list(DEFAULT_FIELD_KEYS) if selected is None else list(selected)
    return client.post(
        "/api/v1/contract-extractions",
        files={"file": ("msa.pdf", SOURCE_BYTES, "application/pdf")},
        data={"selected_fields": chosen},
    )


# --------------------------------------------------------------------------- #
# GET /fields
# --------------------------------------------------------------------------- #


def test_fields_endpoint_serves_the_single_source_of_truth(client: TestClient) -> None:
    response = client.get("/api/v1/contract-extractions/fields")

    assert response.status_code == 200
    body = response.json()
    assert [field["key"] for field in body["fields"]] == list(CANONICAL_FIELD_KEYS)
    assert len(body["default_fields"]) == 5
    # Every one of the ten is selectable; `default_fields` only says which five the
    # picker starts with.
    assert "optional_fields" not in body
    assert sum(1 for field in body["fields"] if field["default_selected"]) == 5
    assert all(field["description"] for field in body["fields"])


# --------------------------------------------------------------------------- #
# POST "" — selection validation
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "selected",
    [
        [],  # nothing to extract
        ["not_a_field"],  # unknown
        ["governing_law", "governing_law"],  # duplicate
    ],
)
def test_an_invalid_selection_is_422(client: TestClient, selected: list[str]) -> None:
    assert _upload(client, selected).status_code == 422


def test_a_formerly_fixed_key_is_now_an_ordinary_selection(
    client: TestClient,
) -> None:
    """`contract_title` used to be rejected as un-selectable. It is a normal key."""

    response = _upload(client, ["contract_title"])

    assert response.status_code == 200
    assert response.json()["selected_fields"] == ["contract_title"]


def test_extract_with_the_default_five_selected(client: TestClient) -> None:
    response = _upload(client, list(DEFAULT_FIELD_KEYS))

    assert response.status_code == 200
    body = response.json()
    assert tuple(body["fields"]) == CANONICAL_FIELD_KEYS
    assert body["extraction_status"] == "complete"
    assert body["selected_fields"] == list(DEFAULT_FIELD_KEYS)
    assert body["fields"]["contract_title"] == "Master Services Agreement"
    assert body["fields"]["parties"] == "Acme Corp, Inc.; Northwind Ltd."
    assert body["fields"]["effective_date"] == "15/01/2026"
    assert body["fields"]["contract_value"] == "USD 250000.00"
    # Present and blank, because they were never requested.
    assert body["fields"]["governing_law"] == ""
    assert body["unresolved_fields"] == []


def test_a_single_field_selection_extracts_only_that_field(
    client: TestClient,
) -> None:
    """One field on the right is enough to extract, and the other nine stay blank."""

    response = _upload(client, ["governing_law"])

    assert response.status_code == 200
    body = response.json()
    assert tuple(body["fields"]) == CANONICAL_FIELD_KEYS
    assert body["selected_fields"] == ["governing_law"]
    assert body["fields"]["governing_law"] == "State of Delaware"
    # Everything not asked for is blank — including the formerly-fixed five, which
    # the extractor could have found but was never asked to.
    for key in CANONICAL_FIELD_KEYS:
        if key != "governing_law":
            assert body["fields"][key] == "", key
    assert body["extraction_status"] == "complete"
    assert body["unresolved_fields"] == []


def test_extract_with_a_default_field_deselected(client: TestClient) -> None:
    """Every field is deselectable now — dropping `parties` must leave it blank and
    must not count as a failure."""

    selected = [key for key in DEFAULT_FIELD_KEYS if key != "parties"]
    body = _upload(client, selected).json()

    assert body["selected_fields"] == selected
    assert body["fields"]["parties"] == ""
    assert body["extraction_status"] == "complete"
    assert body["unresolved_fields"] == []


def test_all_ten_keys_for_every_selection(client: TestClient) -> None:
    from app.contract_fields.catalogue import NON_DEFAULT_FIELD_KEYS

    for selected in (
        ["contract_title"],
        list(DEFAULT_FIELD_KEYS),
        ["payment_terms"],
        list(NON_DEFAULT_FIELD_KEYS),
        list(CANONICAL_FIELD_KEYS),
    ):
        body = _upload(client, list(selected)).json()
        assert tuple(body["fields"]) == CANONICAL_FIELD_KEYS
        assert len(body["fields"]) == 10


# --------------------------------------------------------------------------- #
# The failure rule over HTTP
# --------------------------------------------------------------------------- #


def test_a_blank_requested_field_is_200_and_persisted(client: TestClient) -> None:
    client.use_document(INCOMPLETE_CONTRACT)  # type: ignore[attr-defined]

    response = _upload(client)

    # A business outcome, not a transport error.
    assert response.status_code == 200
    body = response.json()
    assert body["extraction_status"] == "needs_verification"
    assert [entry["field_key"] for entry in body["unresolved_fields"]] == [
        "term_end_date"
    ]
    assert body["unresolved_fields"][0]["reason"] == "not_found"

    # ...and the row the human works from is there.
    stored = client.get(f"/api/v1/contract-extractions/{body['extraction_id']}")
    assert stored.status_code == 200
    assert stored.json()["extraction_status"] == "needs_verification"


def test_an_unselected_blank_stays_complete(client: TestClient) -> None:
    body = _upload(client).json()

    assert body["fields"]["notice_period"] == ""
    assert body["extraction_status"] == "complete"


# --------------------------------------------------------------------------- #
# Owner scoping
# --------------------------------------------------------------------------- #


def test_another_owners_extraction_is_404(client: TestClient) -> None:
    extraction_id = _upload(client).json()["extraction_id"]

    app.dependency_overrides[get_current_user] = lambda: _user(
        OTHER_ID, "other@example.com"
    )
    assert (
        client.get(f"/api/v1/contract-extractions/{extraction_id}").status_code == 404
    )
    assert (
        client.get(f"/api/v1/contract-extractions/{extraction_id}/source").status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/contract-extractions/{extraction_id}/verify",
            json={"action": "save", "values": {}},
        ).status_code
        == 404
    )


def test_records_are_owner_scoped_and_filterable(client: TestClient) -> None:
    _upload(client)
    client.use_document(INCOMPLETE_CONTRACT)  # type: ignore[attr-defined]
    _upload(client)

    page = client.get("/api/v1/contract-extractions/records").json()
    assert page["count"] == 2

    failures = client.get(
        "/api/v1/contract-extractions/records",
        params={"extraction_status": "needs_verification"},
    ).json()
    assert failures["count"] == 1
    assert failures["data"][0]["extraction_status"] == "needs_verification"

    app.dependency_overrides[get_current_user] = lambda: _user(
        OTHER_ID, "other@example.com"
    )
    assert client.get("/api/v1/contract-extractions/records").json()["count"] == 0


# --------------------------------------------------------------------------- #
# PATCH /{id}/verify
# --------------------------------------------------------------------------- #


def _failed_extraction(client: TestClient) -> str:
    client.use_document(INCOMPLETE_CONTRACT)  # type: ignore[attr-defined]
    return str(_upload(client).json()["extraction_id"])


def test_approve_is_refused_while_a_field_is_still_blank(client: TestClient) -> None:
    extraction_id = _failed_extraction(client)

    response = client.patch(
        f"/api/v1/contract-extractions/{extraction_id}/verify",
        json={"action": "approve", "values": {}},
    )

    assert response.status_code == 422
    assert "term_end_date" in response.json()["detail"]


def test_save_keeps_the_failure_standing(client: TestClient) -> None:
    extraction_id = _failed_extraction(client)

    body = client.patch(
        f"/api/v1/contract-extractions/{extraction_id}/verify",
        json={"action": "save", "values": {"term_end_date": "14/01/2027"}},
    ).json()

    assert body["extraction_status"] == "needs_verification"
    assert body["verified_values"] == {"term_end_date": "14/01/2027"}
    # The machine column is untouched.
    assert body["fields"]["term_end_date"] == ""


def test_approve_after_filling_the_blank(client: TestClient) -> None:
    extraction_id = _failed_extraction(client)

    body = client.patch(
        f"/api/v1/contract-extractions/{extraction_id}/verify",
        json={"action": "approve", "values": {"term_end_date": "14/01/2027"}},
    ).json()

    assert body["extraction_status"] == "verified"
    assert body["fields"]["term_end_date"] == ""
    assert body["verified_values"]["term_end_date"] == "14/01/2027"


def test_reject_records_the_decision(client: TestClient) -> None:
    extraction_id = _failed_extraction(client)

    body = client.patch(
        f"/api/v1/contract-extractions/{extraction_id}/verify",
        json={"action": "reject", "values": {}, "note": "wrong document"},
    ).json()

    assert body["extraction_status"] == "rejected"


def test_verifying_a_never_requested_key_is_422(client: TestClient) -> None:
    extraction_id = _failed_extraction(client)

    response = client.patch(
        f"/api/v1/contract-extractions/{extraction_id}/verify",
        json={"action": "save", "values": {"termination_clause": "invented"}},
    )

    assert response.status_code == 422


def test_verifying_an_unknown_key_is_422(client: TestClient) -> None:
    extraction_id = _failed_extraction(client)

    response = client.patch(
        f"/api/v1/contract-extractions/{extraction_id}/verify",
        json={"action": "save", "values": {"not_a_field": "x"}},
    )

    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# GET /{id}/source
# --------------------------------------------------------------------------- #


def test_source_serves_the_stored_document(client: TestClient) -> None:
    extraction_id = _upload(client).json()["extraction_id"]

    response = client.get(f"/api/v1/contract-extractions/{extraction_id}/source")

    assert response.status_code == 200
    assert response.content == SOURCE_BYTES
    assert response.headers["x-content-type-options"] == "nosniff"


# --------------------------------------------------------------------------- #
# The provider is optional, and its absence is never a 500
# --------------------------------------------------------------------------- #


def test_a_failing_provider_still_returns_a_persisted_result(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.contract_fields.extractor as extractor

    def _unauthorized(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise RuntimeError("401 Unauthorized")

    monkeypatch.setattr(extractor, "extract_with_provider", _unauthorized)
    client.use_document(  # type: ignore[attr-defined]
        [("paragraph", "A page with nothing extractable on it.")]
    )

    response = _upload(client, ["governing_law"])

    # Degraded, not failed: 200, a persisted row, blanks with a stated reason.
    assert response.status_code == 200
    body = response.json()
    assert body["extraction_status"] == "needs_verification"
    assert tuple(body["fields"]) == CANONICAL_FIELD_KEYS
    # The deterministic pass still finds a title; everything that needed the
    # provider is blank rather than guessed.
    assert body["fields"]["effective_date"] == ""
    assert body["fields"]["contract_value"] == ""
    assert body["fields"]["governing_law"] == ""
    reasons = {entry["reason"] for entry in body["unresolved_fields"]}
    assert reasons == {"provider_unavailable"}
    assert any("provider was unavailable" in warning for warning in body["warnings"])
    assert (
        client.get(f"/api/v1/contract-extractions/{body['extraction_id']}").status_code
        == 200
    )


def test_a_fully_labelled_contract_reaches_complete(client: TestClient) -> None:
    """The deterministic happy path, with every optional field selected.

    Pinned because the grounding fences are the kind of change that quietly blanks
    the ordinary case: an earlier revision made three of the five optional fields
    unresolvable and turned this exact document into `needs_verification`.
    """

    client.use_document(TEN_FIELD_CONTRACT)  # type: ignore[attr-defined]

    # All ten selected: every key is in scope, so every key must come back filled.
    body = _upload(client, list(CANONICAL_FIELD_KEYS)).json()

    assert body["extraction_status"] == "complete"
    assert body["unresolved_fields"] == []
    assert body["fields"] == {
        "contract_title": "Master Services Agreement",
        "parties": "Acme Corp, Inc.; Northwind Ltd.",
        "effective_date": "15/01/2026",
        "term_end_date": "14/01/2027",
        "contract_value": "USD 250000.00",
        "governing_law": "State of Delaware",
        "payment_terms": "Net 30",
        "notice_period": "90 days' prior written notice",
        "renewal_terms": "Automatic renewal",
        # Not truncated to "on notice": the earliest label match wins, not the
        # first pattern in tuple order.
        "termination_clause": "Termination for convenience on notice",
    }
