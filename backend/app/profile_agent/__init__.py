"""Profile chat agent: a public, document-grounded, privilege-free assistant.

Stage 1 prompt-stuffing architecture (no vector DB): all markdown docs in
``docs/`` are concatenated into the system prompt at request time and cached in
memory with an mtime check. The endpoint has zero privileges (no tool calling, no
DB writes, no fetching) so a successful jailbreak can only produce wrong words,
never actions or data leakage beyond the public docs.
"""
