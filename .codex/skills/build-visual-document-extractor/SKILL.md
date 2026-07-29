---
name: build-visual-document-extractor
description: Build, extend, diagnose, or verify an application that extracts text and structured fields from PDF, DOCX, PPTX, and images using Docling, PaddleOCR or PaddleOCR-VL, MinerU or Marker, and secondary-parser or vision-model fallbacks, with a side-by-side human-validation UI and an acceptance-driven verification loop.
---

# Build a visual document extractor

> Codex compatibility: place this content in `SKILL.md` inside a folder named `build-visual-document-extractor` to install it as a Codex skill. Keep `AGENT.md` beside the project for its full agent and acceptance contract; rename it to repository-root `AGENTS.md` for automatic repository instruction loading.

## Establish scope

Read repository instructions and inspect the existing application, tests, dependencies, and working-tree changes. Preserve unrelated user work.

Read repository-root `AGENTS.md` for the authoritative architecture, roles, normalized schema, verification loop, acceptance criteria, protected paths, and approval gates. If it is unavailable, apply the requirements in this skill and create a traceable acceptance checklist before coding.

For the `mnsai` repository, inspect the existing GPT OCR flow for context, but treat it as
protected legacy behavior:

- `backend/app/gptocr/**`
- `backend/app/tests/gptocr/**`
- `backend/app/api/routes/extractorgpt.py`
- the existing `/api/v1/gptfiles/ocr` and `/api/v1/gptfiles/ocr-json` contracts

Do not edit, relocate, reformat, delete, or import internal implementation from those
paths for the new extractor. Build the new backend as the independent sibling package
`backend/app/visual_document_extractor/`, with tests under
`backend/app/tests/visual_document_extractor/`. Keep new frontend review routes and
components separate from the existing GPT OCR proxy routes unless the user explicitly
approves integration. Any later router or application registration must be additive and
must preserve existing behavior.

When the user requests an instruction-review phase before implementation, update only
the instruction files they identified, summarize the intended package and integration
boundary, and stop for verification. During that approval gate, do not create the package,
add dependencies, edit application code, register routes, create migrations, or scaffold
frontend files.

Build toward this outcome:

- route digital PDF/DOCX/PPTX through Docling;
- route scanned PDF/images through PaddleOCR or PaddleOCR-VL;
- route formula-heavy/scientific documents through MinerU or Marker;
- route low-confidence or failed pages through a different secondary parser and then a configured vision model;
- present the original page and extracted text/fields side by side for human correction and approval.

## Plan contracts first

Define or confirm:

1. A parser-adapter interface with page-level input, normalized output, structured errors, timeout, parser name/version, and quality signals.
2. A normalized schema containing document/page IDs, classification, elements, text/fields, bounding boxes, coordinate space, reading order, confidence or quality signal, warnings, attempts, selected parser, and review state.
3. Job states such as `queued`, `classifying`, `extracting`, `fallback`, `needs_review`, `approved`, `failed`, and `cancelled`.
4. Configurable routing thresholds, retry limits, and feature flags for optional heavyweight or remote models.
5. API and UI contracts for source preview, extraction results, corrections, approvals, reprocessing, and audit history.

Do not couple the UI or persistence layer directly to any parser’s native response.

For this repository, the pre-implementation plan must also name:

1. The new API prefix and how it avoids collisions with `/api/v1/gptfiles/*`.
2. The modules to be created inside `backend/app/visual_document_extractor/`.
3. The dedicated test and fixture locations.
4. Additive router, configuration, database, worker, and frontend integration points.
5. A compatibility check proving that protected GPT OCR endpoints and tests remain
   unchanged.

## Implement incrementally

Prefer vertical slices that can be demonstrated:

1. Upload one supported document and render a stable page preview.
2. Extract one page through the correct adapter and normalize it.
3. Display the page and extraction side by side.
4. Link element selection to source bounding boxes.
5. Save corrections separately from immutable parser output.
6. Add classification and page-level routing.
7. Add deterministic quality validation.
8. Add secondary-parser and vision-model fallbacks with bounded retries.
9. Add approval, rejection, reprocessing, audit, export, security, and operational controls.

Keep optional parsers behind adapters so the application can start and report capability status even when a heavyweight model is not installed.

## Route pages

Use native-text availability, raster coverage, character plausibility, layout signals, and formula/scientific signals. Support mixed documents by routing per page where useful.

```text
Digital PDF / DOCX / PPTX  → Docling
Scanned PDF / image        → PaddleOCR → PaddleOCR-VL for complex layouts
Formula-heavy/scientific   → MinerU or Marker
Low-confidence/failed page → different secondary parser → configured vision model
```

Record the chosen route and reason. Allow an operator override. Do not OCR an adequate native-text page without a specific reason.

## Validate extraction quality

Combine provider confidence, when available, with deterministic checks:

- non-empty plausible text;
- valid reading order and non-duplicated elements;
- coordinates inside the declared page space;
- table structure present when a table was detected;
- formula preservation on formula-heavy pages;
- acceptable noise/replacement-character ratios;
- expected text-density range;
- no adapter error or timeout.

Never fabricate confidence. Store `null` and a separate quality assessment when an adapter does not provide calibrated confidence.

## Escalate safely

On a failed quality gate:

1. Retry only transient failures within the retry budget.
2. Run a materially different parser on only the affected page.
3. compare candidates using deterministic checks and calibrated signals.
4. If still unresolved, call the configured vision model with the page/crop and minimal necessary context.
5. Validate structured model output against the normalized schema.
6. Mark model-derived values and record provider, model, prompt version, and attempt.
7. Set `manual_review_required` when uncertainty remains.

Never loop indefinitely and never silently fill missing text.

## Build the review UI

On desktop, show the original page on the left and extracted text/fields on the right. On narrow screens, use an accessible stacked layout.

Include:

- page/slide navigation, thumbnails, zoom, pan, rotate, and fit;
- linked page regions and extracted elements;
- editable text and fields;
- confidence, warning, parser, and fallback details;
- save, approve, reject, and reprocess controls;
- loading, empty, error, and partial-success states;
- unsaved-change protection, keyboard operation, and accessible labels;
- immutable original output plus separately stored reviewed values and audit history.

Sanitize all extracted content before rendering.

## Coordinate specialized agents

Let the orchestrator own shared contracts, integration, the acceptance checklist, and final completion. Delegate bounded work to specialists for:

- intake and page classification;
- extraction adapters;
- quality and fallback routing;
- backend and persistence;
- human-validation UI;
- independent verification.

Give each agent explicit files, interfaces, expected tests, and reporting requirements. Avoid concurrent edits to the same files unless coordination is explicit.

## Verify continuously

After each vertical slice:

1. Run focused unit and adapter-contract tests.
2. Run real-fixture integration tests.
3. Exercise the review UI end to end.
4. Test timeouts, corrupt files, unsupported/encrypted/oversized inputs, retries, cancellation, and authorization.
5. Compare results with a versioned ground-truth fixture set using appropriate metrics such as character/word error rate, exact field accuracy, formula checks, and coordinate validity.
6. Map evidence to the acceptance checklist.
7. For every failure, diagnose the root cause, add a regression test, fix it, and rerun affected and broader tests.

After the user approves implementation, continue until all acceptance criteria in
repository-root `AGENTS.md` pass. Do not declare success based only on mocked tests, a
working happy path, or compilation.

## Report completion

Report:

- supported formats and active parser routes;
- fallback and manual-review behavior;
- human-validation features;
- tests and fixtures executed with results;
- acceptance-criterion evidence;
- required credentials/models/configuration;
- known limitations and remaining lower-severity risks.

If an external dependency blocks completion, complete all unblocked work and state the exact missing dependency and affected acceptance criteria. Do not represent a blocked criterion as passed.
