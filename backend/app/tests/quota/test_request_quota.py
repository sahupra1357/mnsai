"""The lifetime per-user request quota.

Metered endpoints hang off `QuotaUser`. What matters is the behaviour that
dependency guarantees, so these tests drive a throwaway route wired to the real
dependency against a real (sqlite) session, plus the two user-facing surfaces:
the 402 body the frontend redirects on, and `/users/me/quota`.
"""

import uuid
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api.deps import (
    QUOTA_EXCEEDED_CODE,
    QUOTA_REDIRECT_PATH,
    QuotaUser,
    get_current_user,
    get_db,
)
from app.models import User

USER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000c3")
SUPER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000d4")


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as active:
        active.add(
            User(
                id=USER_ID,
                email="metered@example.com",
                hashed_password="hashed",
                is_active=True,
                request_limit=3,
                request_count=0,
            )
        )
        active.add(
            User(
                id=SUPER_ID,
                email="root@example.com",
                hashed_password="hashed",
                is_active=True,
                is_superuser=True,
                request_limit=3,
                request_count=0,
            )
        )
        active.commit()
        yield active


def _app(session: Session, actor_id: uuid.UUID) -> FastAPI:
    """A minimal app with one metered route and one that deliberately blows up.

    `get_current_user` reads the live row, exactly as the real dependency does,
    so a spent quota is visible to the next request.
    """
    api = FastAPI()

    @api.post("/metered")
    def metered(user: QuotaUser) -> dict[str, str]:
        return {"owner": str(user.id)}

    @api.post("/broken")
    def broken(_: QuotaUser) -> dict[str, str]:
        raise RuntimeError("endpoint blew up")

    api.dependency_overrides[get_db] = lambda: session
    api.dependency_overrides[get_current_user] = lambda: session.get(User, actor_id)
    return api


def _count(session: Session, user_id: uuid.UUID) -> int:
    session.expire_all()
    user = session.get(User, user_id)
    assert user is not None
    return user.request_count


def test_each_call_spends_one_request(session: Session) -> None:
    with TestClient(_app(session, USER_ID)) as client:
        assert client.post("/metered").status_code == 200
        assert _count(session, USER_ID) == 1
        assert client.post("/metered").status_code == 200
        assert _count(session, USER_ID) == 2


def test_request_past_the_limit_is_refused_with_402(session: Session) -> None:
    with TestClient(_app(session, USER_ID)) as client:
        for _ in range(3):
            assert client.post("/metered").status_code == 200

        response = client.post("/metered")

    assert response.status_code == 402
    detail = response.json()["detail"]
    assert detail["code"] == QUOTA_EXCEEDED_CODE
    assert detail["redirect"] == QUOTA_REDIRECT_PATH
    assert detail["limit"] == 3
    assert detail["used"] == 3
    # The refused call is not itself charged.
    assert _count(session, USER_ID) == 3


def test_raising_the_limit_lets_the_user_continue(session: Session) -> None:
    with TestClient(_app(session, USER_ID)) as client:
        for _ in range(3):
            client.post("/metered")
        assert client.post("/metered").status_code == 402

        user = session.get(User, USER_ID)
        assert user is not None
        user.request_limit = 5
        session.add(user)
        session.commit()

        assert client.post("/metered").status_code == 200
    assert _count(session, USER_ID) == 4


def test_resetting_the_count_lets_the_user_continue(session: Session) -> None:
    with TestClient(_app(session, USER_ID)) as client:
        for _ in range(3):
            client.post("/metered")

        user = session.get(User, USER_ID)
        assert user is not None
        user.request_count = 0
        session.add(user)
        session.commit()

        assert client.post("/metered").status_code == 200
    assert _count(session, USER_ID) == 1


def test_superuser_is_never_metered(session: Session) -> None:
    with TestClient(_app(session, SUPER_ID)) as client:
        for _ in range(10):
            assert client.post("/metered").status_code == 200
    assert _count(session, SUPER_ID) == 0


def test_a_failed_request_is_not_charged(session: Session) -> None:
    client = TestClient(_app(session, USER_ID), raise_server_exceptions=False)
    assert client.post("/broken").status_code == 500
    assert _count(session, USER_ID) == 0


def test_zero_limit_refuses_the_very_first_request(session: Session) -> None:
    user = session.get(User, USER_ID)
    assert user is not None
    user.request_limit = 0
    session.add(user)
    session.commit()

    with TestClient(_app(session, USER_ID)) as client:
        assert client.post("/metered").status_code == 402
    assert _count(session, USER_ID) == 0
