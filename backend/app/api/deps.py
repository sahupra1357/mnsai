from collections.abc import Generator
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import TokenPayload, User

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


QUOTA_EXCEEDED_CODE = "quota_exceeded"
QUOTA_REDIRECT_PATH = "/pricing?reason=quota"


def quota_exceeded_detail(user: User) -> dict[str, Any]:
    """The 402 body. `code` is what the frontend matches on; `redirect` is where
    it sends the user. Kept structured so the UI never parses prose."""
    return {
        "code": QUOTA_EXCEEDED_CODE,
        "message": (
            f"You have used all {user.request_limit} of your free requests. "
            "Subscribe to continue."
        ),
        "limit": user.request_limit,
        "used": user.request_count,
        "redirect": QUOTA_REDIRECT_PATH,
    }


def consume_request_quota(
    session: SessionDep, current_user: CurrentUser
) -> Generator[User, None, None]:
    """Meters one request against the caller's lifetime quota.

    Superusers pass through unmetered. Everyone else is refused with 402 once
    `request_count` reaches `request_limit`.

    The count is incremented *after* the endpoint returns, and only when it did
    not raise: a request that fails on our side should not cost the user one of
    their five. The check itself is not transactional, so two genuinely
    simultaneous requests can both pass on the last remaining unit; the ceiling
    is a product limit, not a billing ledger, and one extra call is cheaper than
    locking the user row on every metered endpoint.
    """
    if current_user.is_superuser:
        yield current_user
        return

    if current_user.request_count >= current_user.request_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=quota_exceeded_detail(current_user),
        )

    yield current_user

    # Re-read inside this session: the endpoint may have committed its own work
    # and expired the instance we checked above.
    user = session.get(User, current_user.id)
    if user is not None:
        user.request_count += 1
        session.add(user)
        session.commit()


QuotaUser = Annotated[User, Depends(consume_request_quota)]
