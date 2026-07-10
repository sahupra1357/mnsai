"""Security primitives for the public profile-chat endpoint.

Defense in depth — no single layer is trusted. See the ``profile-chat-agent``
skill for the five-layer spec. This module holds the deterministic (non-LLM)
pieces so they can be unit-tested in isolation:

- Layer 1: request validation models, caps, injection pre-filter, per-IP rate limit
- Layer 2: the canary token (generated once per process / "deploy")
- Layer 4: the output guard (canary + verbatim-doc-dump detection)
- Layer 5: the global daily request/token budget, plus structured abuse logging
"""
from __future__ import annotations

import logging
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from typing import Literal

from pydantic import BaseModel, field_validator

from app.profile_agent.doc_loader import normalize

logger = logging.getLogger("profile_agent.security")

# ---------------------------------------------------------------------------
# Caps (Layer 1)
# ---------------------------------------------------------------------------
MAX_MESSAGES = 20
MAX_CHARS_PER_MESSAGE = 2000
MAX_TOTAL_CHARS = 12000  # bounded overall body size across all messages
MAX_RESPONSE_TOKENS = 500  # cap on the completion (Layer 4)
MAX_RESPONSE_CHARS = 4000  # hard char cap on streamed output (Layer 4)

# ---------------------------------------------------------------------------
# Rate limit + budget (Layers 1 & 5)
# ---------------------------------------------------------------------------
RATE_LIMIT_PER_MIN = 10  # per IP
RATE_LIMIT_WINDOW_SECONDS = 60
DAILY_REQUEST_BUDGET = 2000  # global, all IPs
DAILY_TOKEN_BUDGET = 400_000  # global, approximate (prompt + completion)

# ---------------------------------------------------------------------------
# Standard messages
# ---------------------------------------------------------------------------
REFUSAL_MESSAGE = (
    "I can only help with questions about Pradeep's skills, experience, and "
    "services. For anything else — or to start a project — reach him directly at "
    "sahupra1357@gmail.com."
)
BUDGET_MESSAGE = (
    "The assistant is resting for now to keep things running smoothly. Please "
    "email Pradeep directly at sahupra1357@gmail.com and he'll get right back to "
    "you."
)
RATE_LIMIT_MESSAGE = (
    "You're sending messages a little too quickly. Please wait a moment and try "
    "again."
)

# ---------------------------------------------------------------------------
# Layer 2: canary token — random per process start ("per deploy"), never output.
# ---------------------------------------------------------------------------
CANARY_TOKEN = f"CANARY-{secrets.token_hex(16)}"


# ---------------------------------------------------------------------------
# Layer 1: request validation models
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    # NOTE: only user/assistant accepted. A ``system`` role in client-sent history
    # is rejected here (forged-history defense) — client history is untrusted.
    role: Literal["user", "assistant"]
    content: str

    @field_validator("content")
    @classmethod
    def _content_length(cls, v: str) -> str:
        if len(v) > MAX_CHARS_PER_MESSAGE:
            raise ValueError(
                f"message exceeds {MAX_CHARS_PER_MESSAGE} characters"
            )
        return v


class ChatRequest(BaseModel):
    messages: list[ChatMessage]

    @field_validator("messages")
    @classmethod
    def _validate_messages(cls, v: list[ChatMessage]) -> list[ChatMessage]:
        if not v:
            raise ValueError("messages must not be empty")
        if len(v) > MAX_MESSAGES:
            raise ValueError(f"too many messages (max {MAX_MESSAGES})")
        total = sum(len(m.content) for m in v)
        if total > MAX_TOTAL_CHARS:
            raise ValueError("total message size too large")
        if v[-1].role != "user":
            raise ValueError("the last message must be from the user")
        return v


# ---------------------------------------------------------------------------
# Layer 1: lightweight injection pre-filter (flag + log, NOT a hard block)
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?(?:the\s+)?(?:previous|above|prior|earlier|your)\s+(?:instructions|prompts?|rules|directions)",
    r"disregard\s+(?:all\s+)?(?:previous|above|prior|your)\s+(?:instructions|rules|prompts?)",
    r"you\s+are\s+now\b",
    r"you\s+are\s+no\s+longer\b",
    r"pretend\s+(?:to\s+be|you\s+are|you\s+have)",
    r"act\s+as\s+(?:if|though|a\b)",
    r"developer\s+mode",
    r"\bDAN\b",
    r"do\s+anything\s+now",
    r"jailbreak",
    r"(?:reveal|show|print|repeat|display|output|summar\w+|translat\w+|reproduce)\s+(?:me\s+)?(?:your|the|all|everything)?\s*(?:system\s+prompt|instructions|initial\s+prompt|rules|prompt\b)",
    r"repeat\s+(?:everything|all|the\s+text)\s+(?:above|before)",
    r"what\s+(?:are|were)\s+your\s+(?:instructions|rules|system\s+prompt)",
    r"role[-\s]?play",
    r"hypothetical(?:ly)?\b",
    r"without\s+(?:any\s+)?(?:restrictions|rules|filters|limitations)",
    r"one\s+letter\s+per\s+line",
    r"spell\s+(?:it|them)\s+out",
    r"verbatim",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)
# A long base64-looking blob is suspicious (obfuscated instructions).
_BASE64_BLOB_RE = re.compile(r"[A-Za-z0-9+/]{80,}={0,2}")


def detect_injection(text: str) -> list[str]:
    """Return the list of matched suspicious patterns (empty = clean)."""
    hits = [m.group(0) for m in _INJECTION_RE.finditer(text)]
    if _BASE64_BLOB_RE.search(text):
        hits.append("<base64-blob>")
    return hits


# ---------------------------------------------------------------------------
# Layer 1 & 5: per-IP rate limit + global daily budget (in-memory)
#
# NOTE: in-memory state is per-process. With multiple backend workers each has
# its own counters; for Stage 1 this is acceptable (the Next.js proxy is the
# single front door and the caps are conservative). A shared store (Redis) would
# be the Stage 2 upgrade.
# ---------------------------------------------------------------------------
class RateLimiter:
    def __init__(self, limit: int = RATE_LIMIT_PER_MIN,
                 window: int = RATE_LIMIT_WINDOW_SECONDS):
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, ip: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            q = self._hits[ip]
            cutoff = now - self.window
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True


class DailyBudget:
    """Global daily request + token budget. Resets on a rolling 24h day key."""

    def __init__(self, request_budget: int = DAILY_REQUEST_BUDGET,
                 token_budget: int = DAILY_TOKEN_BUDGET):
        self.request_budget = request_budget
        self.token_budget = token_budget
        self._day: int | None = None
        self._requests = 0
        self._tokens = 0
        self._lock = threading.Lock()

    def _roll(self, now: float) -> None:
        day = int(now // 86400)
        if day != self._day:
            self._day = day
            self._requests = 0
            self._tokens = 0

    def available(self, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        with self._lock:
            self._roll(now)
            return (
                self._requests < self.request_budget
                and self._tokens < self.token_budget
            )

    def record(self, tokens: int, now: float | None = None) -> None:
        now = time.time() if now is None else now
        with self._lock:
            self._roll(now)
            self._requests += 1
            self._tokens += max(tokens, 0)


rate_limiter = RateLimiter()
daily_budget = DailyBudget()


# ---------------------------------------------------------------------------
# Layer 4: output guard
# ---------------------------------------------------------------------------
VERBATIM_DUMP_THRESHOLD = 400  # contiguous normalized chars matching a doc


def contains_canary(text: str) -> bool:
    return CANARY_TOKEN in text


def contains_verbatim_dump(text: str, docs_normalized: str,
                           threshold: int = VERBATIM_DUMP_THRESHOLD) -> bool:
    """True if any ``threshold``-char window of ``text`` (normalized) is a
    contiguous substring of the (normalized) docs corpus — i.e. a verbatim dump."""
    norm = normalize(text)
    if len(norm) < threshold:
        return False
    # Slide a window; step keeps this cheap for short streamed responses.
    step = 40
    for i in range(0, len(norm) - threshold + 1, step):
        if norm[i:i + threshold] in docs_normalized:
            return True
    return False


class OutputGuard:
    """Stateful guard fed streamed deltas; trips on canary / verbatim dump /
    length cap. Once tripped the caller must abort and emit the refusal."""

    def __init__(self, docs_normalized: str,
                 max_chars: int = MAX_RESPONSE_CHARS,
                 dump_threshold: int = VERBATIM_DUMP_THRESHOLD):
        self._docs_normalized = docs_normalized
        self._max_chars = max_chars
        self._dump_threshold = dump_threshold
        self._buffer = ""
        self.tripped_reason: str | None = None

    @property
    def tripped(self) -> bool:
        return self.tripped_reason is not None

    def feed(self, delta: str) -> bool:
        """Add a delta; return True if the guard just tripped."""
        if self.tripped:
            return False
        self._buffer += delta
        if contains_canary(self._buffer):
            self.tripped_reason = "canary"
        elif len(self._buffer) > self._max_chars:
            self.tripped_reason = "length"
        elif contains_verbatim_dump(
            self._buffer, self._docs_normalized, self._dump_threshold
        ):
            self.tripped_reason = "verbatim_dump"
        return self.tripped


# ---------------------------------------------------------------------------
# Layer 5: structured abuse logging (no full transcripts)
# ---------------------------------------------------------------------------
def log_event(event: str, ip: str, *, detail: str = "",
              user_excerpt: str = "") -> None:
    """Log a flagged/refused/aborted event. Only a truncated excerpt of user
    input is recorded — never a full transcript."""
    excerpt = user_excerpt.replace("\n", " ")[:120]
    logger.warning(
        "profile_chat event=%s ip=%s detail=%s excerpt=%r",
        event, ip, detail, excerpt,
    )
