"""Public, unauthenticated, document-grounded chat endpoint for the profile page.

Security posture (see the ``profile-chat-agent`` skill): assume every request is
adversarial. Defense in depth across five layers; the key invariant is that this
endpoint is PRIVILEGE-FREE — no tool calling, no DB writes, no fetching — so a
fully successful jailbreak can only produce wrong words, never actions or data
leakage beyond the public docs.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError

from app.profile_agent import agent
from app.profile_agent.doc_loader import get_docs
from app.profile_agent.security import (
    BUDGET_MESSAGE,
    RATE_LIMIT_MESSAGE,
    REFUSAL_MESSAGE,
    ChatRequest,
    OutputGuard,
    daily_budget,
    detect_injection,
    log_event,
    rate_limiter,
)

router = APIRouter(prefix="/profile-chat", tags=["profile-chat"])


def _client_ip(request: Request) -> str:
    """Resolve the caller IP, honoring the Next.js proxy's forwarded header."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _sse_text_stream(text: str) -> AsyncIterator[str]:
    async def gen() -> AsyncIterator[str]:
        yield _sse({"delta": text})
        yield _sse({"done": True})
    return gen()


@router.post("/")
async def profile_chat(request: Request):
    ip = _client_ip(request)

    # ---- Layer 1: parse + validate (caps, roles, forged-history rejection) ----
    try:
        raw = await request.body()
    except Exception:
        return JSONResponse({"detail": "invalid body"}, status_code=400)
    if len(raw) > 64_000:  # bounded body size before any parsing cost
        log_event("oversized_body", ip, detail=f"bytes={len(raw)}")
        return JSONResponse({"detail": "request too large"}, status_code=413)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return JSONResponse({"detail": "invalid JSON"}, status_code=400)

    # Reject any client-sent ``system`` role explicitly (forged-history defense);
    # the pydantic model only allows user/assistant, so this yields a clear 400.
    if isinstance(payload, dict):
        for m in payload.get("messages", []) or []:
            if isinstance(m, dict) and m.get("role") == "system":
                log_event("forged_system_role", ip)
                return JSONResponse(
                    {"detail": "system role is not allowed in messages"},
                    status_code=400,
                )
    try:
        chat = ChatRequest.model_validate(payload)
    except ValidationError as e:
        log_event("validation_error", ip, detail=str(e.errors()[:1]))
        return JSONResponse({"detail": "invalid request"}, status_code=400)

    # ---- Layer 1 & 5: per-IP rate limit ----
    if not rate_limiter.allow(ip):
        log_event("rate_limited", ip)
        return JSONResponse({"detail": RATE_LIMIT_MESSAGE}, status_code=429)

    # ---- Layer 5: global daily budget → friendly fallback, no LLM call ----
    if not daily_budget.available():
        log_event("budget_exhausted", ip)
        return StreamingResponse(
            _sse_text_stream(BUDGET_MESSAGE), media_type="text/event-stream"
        )

    # ---- Layer 1: injection pre-filter (flag + log; refusal handled by prompt) ----
    last_user = chat.messages[-1].content
    hits = detect_injection(last_user)
    if hits:
        log_event(
            "injection_flagged", ip,
            detail=",".join(hits[:5]), user_excerpt=last_user,
        )

    docs = get_docs()
    guard = OutputGuard(docs.normalized)

    async def event_stream() -> AsyncIterator[str]:
        produced_chars = 0
        try:
            async for delta in agent.stream_completion(chat.messages):
                produced_chars += len(delta)
                if guard.feed(delta):
                    # ---- Layer 4: output guard tripped — abort + refuse ----
                    log_event(
                        "output_guard_tripped", ip,
                        detail=guard.tripped_reason or "",
                        user_excerpt=last_user,
                    )
                    yield _sse({"replace": REFUSAL_MESSAGE})
                    yield _sse({"done": True})
                    break
                yield _sse({"delta": delta})
            else:
                yield _sse({"done": True})
        except Exception as exc:  # never leak internals to the client
            log_event("llm_error", ip, detail=type(exc).__name__)
            yield _sse({
                "replace": (
                    "Sorry — I ran into a problem answering that. Please try "
                    "again, or email Pradeep at sahupra1357@gmail.com."
                )
            })
            yield _sse({"done": True})
        finally:
            # ---- Layer 5: record approximate usage against the daily budget ----
            approx_tokens = (len(docs.text) + len(last_user) + produced_chars) // 4
            daily_budget.record(approx_tokens)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
