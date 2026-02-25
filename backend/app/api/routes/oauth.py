import uuid
from datetime import timedelta
from typing import Annotated

import httpx
from fastapi import APIRouter, Cookie, HTTPException, Request
from fastapi.responses import RedirectResponse

from app import crud
from app.api.deps import SessionDep
from app.core.config import settings
from app.core.security import create_access_token

router = APIRouter(tags=["oauth"])

PROVIDERS: dict[str, dict[str, str]] = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope": "openid email profile",
    },
    "github": {
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scope": "read:user user:email",
    },
}


def _get_client_credentials(provider: str) -> tuple[str, str]:
    if provider == "google":
        client_id = settings.GOOGLE_CLIENT_ID
        client_secret = settings.GOOGLE_CLIENT_SECRET
    else:
        client_id = settings.GITHUB_CLIENT_ID
        client_secret = settings.GITHUB_CLIENT_SECRET
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail=f"{provider.title()} OAuth is not configured",
        )
    return client_id, client_secret


def _build_redirect_uri(request: Request, provider: str) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}{settings.API_V1_STR}/login/{provider}/callback"


@router.get("/login/{provider}")
async def oauth_login(provider: str, request: Request) -> RedirectResponse:
    frontend_login = f"{settings.FRONTEND_HOST}/login"

    if provider not in PROVIDERS:
        return RedirectResponse(url=f"{frontend_login}?error=unknown_provider")

    try:
        client_id, _ = _get_client_credentials(provider)
    except HTTPException:
        return RedirectResponse(url=f"{frontend_login}?error=provider_not_configured")
    config = PROVIDERS[provider]

    state = str(uuid.uuid4())
    redirect_uri = _build_redirect_uri(request, provider)

    params: dict[str, str] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": config["scope"],
        "state": state,
        "response_type": "code",
    }
    if provider == "google":
        params["access_type"] = "online"

    auth_url = httpx.URL(config["auth_url"]).copy_merge_params(params)
    response = RedirectResponse(url=str(auth_url))
    response.set_cookie(
        "oauth_state",
        state,
        httponly=True,
        samesite="lax",
        max_age=300,
        secure=request.url.scheme == "https",
    )
    return response


@router.get("/login/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    session: SessionDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: Annotated[str | None, Cookie()] = None,
) -> RedirectResponse:
    frontend_login = f"{settings.FRONTEND_HOST}/login"

    if error:
        return RedirectResponse(url=f"{frontend_login}?error={error}")

    if not code:
        return RedirectResponse(url=f"{frontend_login}?error=no_code")

    if not state or state != oauth_state:
        return RedirectResponse(url=f"{frontend_login}?error=state_mismatch")

    if provider not in PROVIDERS:
        return RedirectResponse(url=f"{frontend_login}?error=unknown_provider")

    try:
        client_id, client_secret = _get_client_credentials(provider)
    except HTTPException:
        return RedirectResponse(url=f"{frontend_login}?error=provider_not_configured")

    config = PROVIDERS[provider]
    redirect_uri = _build_redirect_uri(request, provider)

    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        token_res = await client.post(
            config["token_url"],
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
        if token_res.status_code != 200:
            return RedirectResponse(url=f"{frontend_login}?error=token_exchange_failed")

        token_json = token_res.json()
        if "error" in token_json:
            return RedirectResponse(url=f"{frontend_login}?error={token_json['error']}")

        access_token = token_json.get("access_token")
        if not access_token:
            return RedirectResponse(url=f"{frontend_login}?error=no_access_token")

        # Fetch user info
        userinfo_res = await client.get(
            config["userinfo_url"],
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        if userinfo_res.status_code != 200:
            return RedirectResponse(url=f"{frontend_login}?error=userinfo_failed")

        userinfo = userinfo_res.json()

        if provider == "google":
            email: str | None = userinfo.get("email")
            full_name: str | None = userinfo.get("name")
        else:  # github
            email = userinfo.get("email")
            full_name = userinfo.get("name") or userinfo.get("login")
            if not email:
                email = await _fetch_github_primary_email(client, access_token)

    if not email:
        return RedirectResponse(url=f"{frontend_login}?error=no_email")

    user = crud.get_or_create_oauth_user(session=session, email=email, full_name=full_name)

    if not user.is_active:
        return RedirectResponse(url=f"{frontend_login}?error=inactive_user")

    jwt = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    response = RedirectResponse(
        url=f"{settings.FRONTEND_HOST}/api/auth/oauth/callback?token={jwt}"
    )
    response.delete_cookie("oauth_state")
    return response


async def _fetch_github_primary_email(
    client: httpx.AsyncClient, access_token: str
) -> str | None:
    res = await client.get(
        "https://api.github.com/user/emails",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
    )
    if res.status_code != 200:
        return None
    for entry in res.json():
        if entry.get("primary") and entry.get("verified"):
            return entry["email"]
    return None
