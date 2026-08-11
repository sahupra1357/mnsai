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
- Every non-empty parser result is retained as an extraction candidate. The review UI
  defaults to the highest-confidence candidate that passed deterministic quality gates
  and provides a read-only dropdown for inspecting older candidates.
- Revocable, owner-scoped API keys for programmatic multipart uploads. Only API-key
  hashes are stored and the plaintext value is returned once at creation.
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
- Configurable binary storage with Cloudflare R2 as the production default and
  PostgreSQL binary storage as the fallback
- Optional asynchronous Modal dispatch with per-page parser functions, hashed opaque
  source/callback tokens, idempotent result callbacks, and automatic local dispatch
  fallback when Modal cannot accept a job

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

## Storage architecture

PostgreSQL always stores ownership, source checksum and metadata, extraction
fingerprint, normalized results, review corrections, job state, and audit history.
With `DOCUMENT_EXTRACTOR_STORAGE_PROVIDER=r2`, original files and preview PNGs are
stored in R2 and SQL stores only their provider/object references. R2 downloads are
verified against the immutable SHA-256. If R2 configuration is incomplete and
`DOCUMENT_EXTRACTOR_STORAGE_FALLBACK_TO_POSTGRES=True`, binary content is stored in
PostgreSQL instead.

Changing providers does not change the cache key: completed results are still reused
by owner, source SHA-256, and extraction-configuration fingerprint.

## Modal execution architecture

When `DOCUMENT_EXTRACTOR_MODAL_ENABLED=True` and all Modal endpoint settings are
present, uploads are validated and persisted as `queued`, then each classified page is
submitted to the appropriate Modal function. The review frontend polls the existing
document endpoint until all callbacks complete. If dispatch cannot be established, the
queued record is removed and the existing local Render pipeline runs instead.

Low-quality or failed pages use bounded classification-specific Modal chains:
Docling→PaddleOCR for digital/unknown pages, PaddleOCR→PaddleOCR-VL for scans,
MinerU→Marker for formula-heavy pages, and PaddleOCR-VL→MinerU→Marker for complex
layouts. After the Modal chain is exhausted, configured Mistral OCR, OpenAI Terra, and
OpenAI Sol adapters form the remote-provider escalation sequence. An unresolved page is
marked for manual review.

For PostgreSQL binary storage, Modal downloads through a job-bound Render endpoint. For
R2, Modal receives a short-lived R2 presigned URL and bypasses Render for the binary
transfer. Result callbacks always use a separate opaque credential. Only SHA-256 token
digests and non-secret lifecycle metadata are stored; plaintext tokens are sent once in
the protected dispatch request and are never logged.

The Modal submission endpoint is protected with Modal Proxy Auth. A completed result
callback is idempotent by job and attempt ID. Source credentials are revoked at terminal
state; callback credentials remain narrowly usable for bounded duplicate delivery until
expiry.

## Deploy Cloudflare R2

1. In Cloudflare, open **Storage & databases → R2** and activate R2.
2. Create a private bucket, for example `mnsai-documents`. Do not enable public `r2.dev`
   access.
3. Create an R2 API token restricted to that bucket with object read/write permission.
4. Copy the S3 endpoint shown by Cloudflare. It has the form
   `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`.
5. Set these Render variables:

   ```text
   DOCUMENT_EXTRACTOR_STORAGE_PROVIDER=r2
   DOCUMENT_EXTRACTOR_STORAGE_FALLBACK_TO_POSTGRES=True
   DOCUMENT_EXTRACTOR_R2_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
   DOCUMENT_EXTRACTOR_R2_BUCKET=mnsai-documents
   DOCUMENT_EXTRACTOR_R2_ACCESS_KEY_ID=<R2 access key>
   DOCUMENT_EXTRACTOR_R2_SECRET_ACCESS_KEY=<R2 secret key>
   DOCUMENT_EXTRACTOR_R2_PREFIX=visual-document-extractor
   DOCUMENT_EXTRACTOR_R2_PRESIGN_SECONDS=900
   ```

6. Deploy Render, run the Alembic migration, upload a small fixture, and confirm the
   source object exists under the configured prefix while `source_bytes` is null.
7. Set `DOCUMENT_EXTRACTOR_STORAGE_PROVIDER=postgres` to deliberately use PostgreSQL.
   To require R2 rather than fall back, set
   `DOCUMENT_EXTRACTOR_STORAGE_FALLBACK_TO_POSTGRES=False`.

## Deploy Modal

1. Install and authenticate the Modal CLI in a deployment workstation or CI environment:

   ```bash
   python -m pip install modal
   modal setup
   ```

2. Create a Modal Proxy Token for the submission web function:

   ```bash
   modal workspace proxy-tokens create
   ```

   Save the printed token ID and secret immediately; Modal does not show the secret
   again.

3. Review `modal_app.py` and `modal_parser_worker.py`. The repository pins Docling,
   PaddleOCR/PaddleOCR-VL, MinerU, and Marker in separate images and bakes the normalized
   JSON worker into each image. Docling is CPU by default; PaddleOCR uses T4, and
   PaddleOCR-VL/MinerU/Marker use L4 defaults. Confirm Marker model-weight licensing is
   appropriate for your organization before deployment.
4. Adjust a GPU or parser pin only after fixture-based memory, accuracy, and latency
   measurements. Treat model downloads as untrusted deployment inputs and record their
   revisions.
5. Deploy from the `backend/` directory:

   ```bash
   modal deploy modal_app.py
   ```

6. Copy the protected `submit` URL printed by Modal. In Render set:

   ```text
   DOCUMENT_EXTRACTOR_MODAL_ENABLED=True
   DOCUMENT_EXTRACTOR_MODAL_ENDPOINT_URL=<Modal submit URL>
   DOCUMENT_EXTRACTOR_MODAL_KEY=<Proxy Token ID>
   DOCUMENT_EXTRACTOR_MODAL_SECRET=<Proxy Token secret>
   DOCUMENT_EXTRACTOR_PUBLIC_BASE_URL=https://<service>.onrender.com
   DOCUMENT_EXTRACTOR_MODAL_DISPATCH_TIMEOUT_SECONDS=15
   DOCUMENT_EXTRACTOR_MODAL_PARSER_TIMEOUT_SECONDS=900
   DOCUMENT_EXTRACTOR_MODAL_SOURCE_TOKEN_MINUTES=60
   DOCUMENT_EXTRACTOR_MODAL_RESULT_TOKEN_MINUTES=180
   DOCUMENT_EXTRACTOR_MODAL_SOURCE_MAX_USES=3
   ```

7. Redeploy Render and verify `/api/v1/document-extractions/capabilities` reports
   `execution_backend=modal`. Upload one fixture for every route and confirm the Modal
   call ID, parser attempt/version, callback, and final page state.
8. To disable Modal safely, set `DOCUMENT_EXTRACTOR_MODAL_ENABLED=False` and redeploy.
   Uploads then use only adapters available in the Render container.

## Deploy the Render backend

1. Provision durable PostgreSQL. Render Free PostgreSQL expires and is not appropriate
   for retained production documents or audit history.
2. Configure the existing application variables plus the storage variables above.
3. Ensure the build installs the locked backend dependencies (`uv sync --frozen`).
4. Run migrations before starting the API:

   ```bash
   alembic upgrade head
   ```

5. Deploy the FastAPI service and set its health check as already used by the repository.
6. Configure Modal only after the Render public URL is stable, because Modal callbacks
   use `DOCUMENT_EXTRACTOR_PUBLIC_BASE_URL`.
7. Smoke-test upload, queued polling, source/preview access, review save/approve,
   duplicate upload reuse, reprocessing, and deletion.

## Programmatic uploads with an API key

API-key management requires the normal authenticated web/JWT session. Create a named
key with the authenticated endpoint below; copy `api_key` from the response immediately
because it cannot be recovered later:

```bash
curl -X POST "https://<service>.onrender.com/api/v1/document-extractions/api-keys" \
  -H "Authorization: Bearer <user-access-token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"document-ingestion"}'
```

Upload from an application with the returned key. Omit `parser` for automatic routing,
or pass a configured parser such as `paddleocr-vl`:

```bash
curl -X POST "https://<service>.onrender.com/api/v1/document-extractions/programmatic" \
  -H "X-API-Key: <api-key>" \
  -F "file=@/absolute/path/document.pdf" \
  -F "parser=paddleocr-vl"
```

List key metadata with `GET /api/v1/document-extractions/api-keys` and revoke a key
with `DELETE /api/v1/document-extractions/api-keys/{key_id}` using the normal user
access token. Rotate an active key with
`POST /api/v1/document-extractions/api-keys/{key_id}/rotate`; rotation atomically
revokes the old key and returns the replacement plaintext exactly once. The authenticated
settings page provides the same create, copy, rotate, and revoke workflow. Revocation is
immediate. Never place an API key in a browser bundle, query string, source repository,
or logs.

The programmatic endpoint returns the same `DocumentResult` contract as the frontend.
With Modal enabled, a `queued` or `extracting` result is expected. Poll
`GET /api/v1/document-extractions/programmatic/{document_id}` with the same
`X-API-Key` until the document reaches a review state.

R2 and PostgreSQL cannot participate in one atomic transaction. Deletion therefore
fails closed: SQL metadata is retained if an R2 deletion fails so the operation can be
retried. If several objects belong to a document, an interruption after an earlier
object was deleted can temporarily leave a retained record with a missing derived
object. Production operations should retry deletion and alert on object-store failures;
a durable deletion outbox is the recommended next hardening step for strict guarantees.

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
- Local extraction runs synchronously. Modal extraction has a durable per-page job and
  callback boundary, but active remote-job cancellation remains pending.
- Simultaneous first uploads of identical bytes can both begin extraction. Subsequent
  uploads reuse the newest completed matching result.
- Malware scanning requires a separately configured scanner/isolation service.
- Real Tesseract fixture coverage is active. Full Docling/Paddle/MinerU/Marker accuracy,
  UI E2E visual, and accessibility verification require their deployment dependencies.
- Mistral and OpenAI contracts are covered with mocked provider responses. Live remote
  smoke tests require user-supplied API keys and may incur provider charges.
- The Modal images include pinned parser packages and a normalized worker executable,
  but their large model downloads, CUDA compatibility, coordinates, and extraction
  accuracy must be verified against real fixtures in the target Modal account before
  Docling/PaddleOCR/PaddleOCR-VL/MinerU/Marker acceptance criteria can be claimed.
