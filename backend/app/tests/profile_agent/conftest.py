"""Fixtures + helpers for profile-chat tests.

The LLM is mocked for all deterministic tests. Live-LLM red-team cases are opt-in
via the ``PROFILE_CHAT_LIVE=1`` env var (they need a real OPENAI_API_KEY).
"""
import json
import os
from collections.abc import AsyncIterator

import pytest

from app.profile_agent import security

ENDPOINT = "/api/v1/profile-chat/"

LIVE = os.environ.get("PROFILE_CHAT_LIVE") == "1"
requires_live = pytest.mark.skipif(
    not LIVE, reason="set PROFILE_CHAT_LIVE=1 (with a real key) to run live-LLM tests"
)


@pytest.fixture(autouse=True)
def _reset_limiters():
    """Each test starts with clean rate-limit + budget state."""
    security.rate_limiter._hits.clear()
    security.daily_budget._day = None
    security.daily_budget._requests = 0
    security.daily_budget._tokens = 0
    yield


def make_stream(tokens):
    """Return a drop-in async replacement for agent.stream_completion."""
    async def _stream(history) -> AsyncIterator[str]:
        for t in tokens:
            yield t
    return _stream


def parse_sse(text: str):
    """Collect deltas/replace/done events from an SSE response body."""
    deltas, replaced, done = [], None, False
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = json.loads(line[len("data:"):].strip())
        if "delta" in payload:
            deltas.append(payload["delta"])
        if "replace" in payload:
            replaced = payload["replace"]
        if payload.get("done"):
            done = True
    return {"text": "".join(deltas), "replace": replaced, "done": done}


def user(content):
    return {"messages": [{"role": "user", "content": content}]}
