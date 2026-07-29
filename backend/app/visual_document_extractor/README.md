# Visual document extractor

This package is independent of the legacy `app.gptocr` implementation.

## Current executable slice

- Authenticated API at `/api/v1/document-extractions`
- Bounded validation for PDF, DOCX, PPTX, PNG, JPEG, TIFF, BMP, GIF, and WebP
- Per-page measurable classification and parser routing
- Normalized elements, attempts, quality signals, warnings, and provenance
- Retry-bounded distinct-parser and optional vision fallback orchestration
- Owner-scoped source/result access
- Review corrections stored separately from parser text, decisions, reprocessing, and
  audit events
- Capability-driven page reprocessing from the review UI: reviewers can use the
  automatic chain or request an available parser/model such as Tesseract, Mistral OCR,
  GPT-5.6 Terra, or GPT-5.6 Sol. The requested adapter runs first; bounded quality
  fallback remains active, and the requested and selected adapters are audited.
- Durable SQLModel persistence with immutable source bytes, optimistic revisions,
  tenant-scoped reads/writes, cascade deletion, and persisted preview artifacts
- Tenant-scoped extraction reuse: an identical source SHA-256 and extraction
  configuration fingerprint returns the saved normalized result instead of running the
  parsers again. The restored result includes semantic JSON, page elements, coordinates,
  parser history, review corrections, and bounding-box links.
- Killable parser process groups with wall-time, CPU, memory, and concurrency limits
- Real Tesseract extraction with word coordinates and parser confidence
- Stable per-page PNG previews for PDF/images and headless LibreOffice conversion for
  DOCX/PPTX
- Capability reporting when optional parser engines are unavailable

## Optional parser capabilities

Tesseract is enabled automatically when its binary is installed. Docling,
PaddleOCR/PaddleOCR-VL, MinerU, Marker, and remote providers remain isolated behind
process adapters. Configure their JSON worker executables with the
`VISUAL_EXTRACTOR_*_WORKER` variables. Until configured, `/capabilities` reports them
unavailable and affected pages use a distinct available fallback or end in manual review.

When enabled, remote fallbacks run per failed page in this bounded order:
Mistral OCR 4, OpenAI GPT-5.6 Terra, then GPT-5.6 Sol. A local result below the
configured minimum confidence or failing another deterministic quality check enters this
chain. Terra escalates to Sol when its schema/output fails or when sensitive values
(numbers, identifiers, URLs, emails, or negations) disagree with the preceding candidate.
The final candidate is still validated; an unresolved page requires manual review.

Remote adapters use provider APIs and do not import or call `app.gptocr`. Mistral receives
only the selected page for PDFs (or the single uploaded image). OpenAI receives a rendered
PNG plus bounded prior-candidate context. Provider output, credentials, and source text
are not written to logs.

Workers receive normalized `PageInput` JSON on stdin (source bytes are base64 encoded)
and must return schema-valid `AdapterResult` JSON on stdout. Worker stderr is discarded
at the trust boundary.

## Configuration

See `.env.example` for:

- `DOCUMENT_EXTRACTOR_MAX_UPLOAD_BYTES`
- `DOCUMENT_EXTRACTOR_MAX_PAGES`
- `DOCUMENT_EXTRACTOR_MAX_RENDERED_PIXELS`
- `DOCUMENT_EXTRACTOR_PARSER_TIMEOUT_SECONDS`
- `DOCUMENT_EXTRACTOR_TRANSIENT_RETRIES`
- `DOCUMENT_EXTRACTOR_ALTERNATE_ATTEMPTS`
- `DOCUMENT_EXTRACTOR_VISION_ATTEMPTS`
- `DOCUMENT_EXTRACTOR_VISION_ENABLED`
- `DOCUMENT_EXTRACTOR_MINIMUM_CONFIDENCE`
- `DOCUMENT_EXTRACTOR_MISTRAL_ENABLED`
- `DOCUMENT_EXTRACTOR_MISTRAL_MODEL`
- `DOCUMENT_EXTRACTOR_MISTRAL_TIMEOUT_SECONDS`
- `DOCUMENT_EXTRACTOR_OPENAI_VISION_ENABLED`
- `DOCUMENT_EXTRACTOR_OPENAI_DEFAULT_MODEL`
- `DOCUMENT_EXTRACTOR_OPENAI_ESCALATION_MODEL`
- `DOCUMENT_EXTRACTOR_OPENAI_TIMEOUT_SECONDS`
- `MISTRAL_API_KEY`
- `OPENAI_API_KEY`
- `DOCUMENT_EXTRACTOR_MAX_PARSER_PROCESSES`
- `DOCUMENT_EXTRACTOR_PARSER_CPU_SECONDS`
- `DOCUMENT_EXTRACTOR_PARSER_MEMORY_MB`
- `DOCUMENT_EXTRACTOR_PREVIEW_DPI`
- `DOCUMENT_EXTRACTOR_OFFICE_BINARY`
- `DOCUMENT_EXTRACTOR_OFFICE_TIMEOUT_SECONDS`
- `DOCUMENT_EXTRACTOR_USE_DURABLE_STORE`
- `VISUAL_EXTRACTOR_DOCLING_WORKER`
- `VISUAL_EXTRACTOR_PADDLEOCR_WORKER`
- `VISUAL_EXTRACTOR_PADDLEOCR_VL_WORKER`
- `VISUAL_EXTRACTOR_MINERU_WORKER`
- `VISUAL_EXTRACTOR_MARKER_WORKER`

## Verification

From `backend/`:

```bash
.venv/bin/pytest -q app/tests/visual_document_extractor
.venv/bin/ruff check app/visual_document_extractor \
  app/api/routes/document_extractions.py \
  app/tests/visual_document_extractor
.venv/bin/mypy app/visual_document_extractor \
  app/api/routes/document_extractions.py
```

## Extraction reuse

The service computes a SHA-256 digest of the uploaded bytes and a separate fingerprint
of the parser capabilities, versions, routing limits, quality threshold, and operator
override. A completed, reviewable result is reused only when both values match within
the same owner/tenant. Failed, cancelled, queued, or still-processing records are never
cache hits.

This deliberately invalidates the saved extraction when parser availability/version or
quality/routing configuration changes. Existing records created before the cache
fingerprint migration are not reused until they are extracted once under the current
configuration. The upload response sets `reused_extraction: true` when it was loaded
from persistence, and the review UI displays “Loaded from saved extraction.”

Reviewer-triggered page reprocessing does not use the upload cache. It preserves a
snapshot of the prior reviewed extraction, appends the new attempts and audit event, and
stores the newly selected page result in the existing document record.

## Known limitations

- Docling, PaddleOCR/PaddleOCR-VL, MinerU, and Marker are not installed in the current
  development environment; their real worker executables and model weights remain
  deployment inputs.
- Headless LibreOffice is included in the backend container but is not installed on the
  current macOS host. Office preview behavior is contract-tested locally; a container
  smoke test still requires a running Docker daemon.
- DOCX page count remains provisional until its first stable PDF conversion.
- Extraction currently runs synchronously within the request while each parser itself is
  isolated in a killable child process. Durable background queuing and active-job
  cancellation remain pending.
- Simultaneous first uploads of identical bytes can both begin extraction. Subsequent
  uploads reuse the newest completed matching result.
- Malware scanning requires a separately configured scanner/isolation service.
- Real Tesseract fixture coverage is active. Full Docling/Paddle/MinerU/Marker accuracy,
  UI E2E visual, and accessibility verification require their deployment dependencies.
- Mistral and OpenAI contracts are covered with mocked provider responses. Live remote
  smoke tests require user-supplied API keys and may incur provider charges.
