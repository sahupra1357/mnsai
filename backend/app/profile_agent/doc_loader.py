"""Document loader for the profile chat agent.

Loads every markdown file in ``docs/``, concatenates them into a single corpus,
and caches the result in memory. The cache is invalidated automatically when any
doc file's mtime changes, so edits to the docs are picked up without a restart.

This is Stage 1 (prompt-stuffing): the corpus is small enough to live entirely in
the system prompt. No embeddings, no vector store.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

DOCS_DIR = Path(__file__).parent / "docs"


@dataclass(frozen=True)
class DocsCorpus:
    """Immutable snapshot of the loaded docs."""

    #: All docs concatenated, each wrapped with a filename banner.
    text: str
    #: Normalized (whitespace-collapsed, lowercased) corpus for verbatim-dump
    #: detection in the output guard.
    normalized: str
    #: Filenames that were loaded, for logging/diagnostics.
    filenames: tuple[str, ...]


_lock = threading.Lock()
_cache: DocsCorpus | None = None
_cache_signature: tuple[tuple[str, float], ...] | None = None


def normalize(text: str) -> str:
    """Collapse whitespace and lowercase — used for verbatim-dump matching."""
    return " ".join(text.split()).lower()


def _current_signature() -> tuple[tuple[str, float], ...]:
    files = sorted(DOCS_DIR.glob("*.md"))
    return tuple((f.name, f.stat().st_mtime) for f in files)


def _build_corpus() -> DocsCorpus:
    files = sorted(DOCS_DIR.glob("*.md"))
    parts: list[str] = []
    names: list[str] = []
    for f in files:
        content = f.read_text(encoding="utf-8").strip()
        if not content:
            continue
        names.append(f.name)
        parts.append(f"### DOCUMENT: {f.name}\n{content}")
    text = "\n\n".join(parts)
    return DocsCorpus(
        text=text,
        normalized=normalize(text),
        filenames=tuple(names),
    )


def get_docs() -> DocsCorpus:
    """Return the docs corpus, rebuilding only when a file's mtime changed."""
    global _cache, _cache_signature
    signature = _current_signature()
    with _lock:
        if _cache is None or signature != _cache_signature:
            _cache = _build_corpus()
            _cache_signature = signature
        return _cache
