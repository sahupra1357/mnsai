# mnsAI — Project Instructions

Full-stack app: FastAPI backend + Next.js 15 (App Router) frontend.

## Run locally

Whole stack in one shot — db, backend, frontend, migrations and superuser seeding:
```bash
docker compose up -d --wait           # frontend :3000, backend :8000, db :5434
```
`--wait` returns only once all three report healthy. Ordering is enforced by
healthchecks: backend waits for a healthy db, frontend waits for a healthy backend
(so the UI is never served before `prestart.sh` has run migrations and seeded the
first superuser). Both app services are `pull_policy: build`, so `up` always builds
the working tree rather than silently reusing a stale image.

Ports 3000/8000/5434 must be free — stop any `npm run dev` / `uvicorn` first.

Hot-reload development instead (source-synced containers):
```bash
docker compose watch
```

Or run the app processes on the host against the Dockerized db:
```bash
docker compose up -d db
cd frontend && npm run dev
cd backend && POSTGRES_SERVER=localhost POSTGRES_PORT=5434 .venv/bin/uvicorn app.main:app
```
The `POSTGRES_*` overrides are required on the host: `.env` points `POSTGRES_SERVER`
at the remote Render database. Inside compose this is handled already — the override
file sets `POSTGRES_SERVER: db`.

## Stack & conventions
- **Frontend**: Next.js 15 App Router, shadcn/ui + Tailwind v3, TanStack Query v5, react-hook-form, sonner toasts, lucide-react icons.
- **Backend**: FastAPI + SQLModel, routes in `backend/app/api/routes/`, registered in `backend/app/api/main.py`. Config via `backend/app/core/config.py` (`settings`). OpenAI SDK is the LLM provider (`settings.OPENAI_DEPLOYMENT_ID`, default `gpt-4o`).
- **Auth**: HttpOnly cookie JWT via Next.js proxy routes (`app/api/auth/*`). Protected pages guarded by `middleware.ts`. Never put tokens in localStorage.
- **API calls from browser**: through the generated OpenAPI client (`frontend/src/client/`, DO NOT delete/hand-edit) or through Next.js API proxy routes when a cookie/secret must stay server-side.
- **Styling**: use existing shadcn components in `components/ui/`; brand palette is **"Teal & warm paper"** (light: warm cream paper + deep teal accent; dark: blue-slate + bright aqua; `ui-main` utility + shadcn `--primary` tokens carry the teal family — defined in `app/globals.css`). Match the visual language of `app/profile/page.tsx`.
- **Ports**: frontend 3000, backend 8000. CORS: `FRONTEND_HOST=http://localhost:3000`.
- **Routes**: `/` is the workspace dashboard (`app/page.tsx`) and is **public** — it renders for signed-out visitors; the tools it links to are the protected part. `/dashboard` still resolves — it redirects to `/`. The profile/portfolio page is `/profile` (`app/profile/page.tsx`, also public).

## Active initiative: Profile page + AI chat agent

Goal: `frontend/app/profile/page.tsx` (routed at `/profile`, public — no login) is a professional profile/portfolio page for Pradeep Sahu that showcases skills and services so prospective users/customers can engage him for projects. The page embeds a chat box answered by an AI agent grounded in profile documents (resume, project write-ups, service descriptions).

Project skills define how to build this — **load them before working on the feature**:
- `.claude/skills/profile-page/SKILL.md` — page layout, sections, components, design rules.
- `.claude/skills/profile-chat-agent/SKILL.md` — RAG chat agent: document store, backend endpoint, streaming, frontend chat widget.
- `.claude/skills/profile-build-orchestrator/SKILL.md` — **the build workflow**: the main session orchestrates; `profile-page-builder` (`.claude/agents/`) implements, `profile-page-grader` verifies and grades, feedback loops back to the builder. Hard cap of 3 rounds plus a no-progress guard — never loop beyond that.

Content sources (never invent facts beyond these):
- `docs/resume.md` — Pradeep's resume, the ground truth.
- `docs/profile-draft.md` — approved page copy derived from the resume; items marked `[NEEDS INPUT]` must be omitted until Pradeep fills them in.

Source-of-truth documents for the chat agent live in `backend/app/profile_agent/docs/` (markdown). The agent must answer **only** from those documents and decline out-of-scope questions.

**Backups & drafts (never edit or delete; all self-contained, linked in nav Resources dropdown):**
- `frontend/app/_archive/product-landing.tsx` — the original product landing page (not routed; may be restored later).
- `frontend/app/drafts/profile-v1/` — frozen 1st profile draft (generic card grid), routed at `/drafts/profile-v1`.
- `frontend/app/drafts/profile-v2/` — frozen 2nd profile draft ("evidence-driven dossier"), routed at `/drafts/profile-v2`.
The live rebuild may freely rewrite `components/profile/*` and `lib/profile-data.ts`; the drafts don't depend on them.

**Current status (July 2026):** chat agent (Phase 2) shipped and graded PASS 97/100 — security layers live, but the `OPENAI_API_KEY` in `.env` is invalid (401), so real completions need a new key. Profile page **v3 redesign** is active: mirror a reference portfolio's format (spec in the profile-page skill, "Design direction v3") with blank placeholders for missing content — never invented facts. Chat security remains gated per `.claude/skills/profile-chat-agent/SKILL.md`; the endpoint stays privilege-free (no tools, no DB writes, no fetching).

**Model policy for the build loop:** orchestrator (main session) runs on **Fable 5**; both subagents (`profile-page-builder`, `profile-page-grader`) run on **Opus** via `model: opus` in their frontmatter — never pass a `model` override when spawning them.

**Autonomous-execution guardrails (all agents, no babysitting):** commands that are read-only or scoped to this project folder / the session scratchpad and reversible via git are acceptable — decide and continue without asking the user. Forbidden everywhere: `sudo`, `rm -rf`, mutating git commands (commit/push/reset/checkout/clean), force flags, remote-script execution (`curl | sh`), destructive docker/db operations, killing processes you didn't start, writes outside the project folder, editing `.env*` secrets. If blocked by these rules, report BLOCKED — don't work around the guardrail and don't ask mid-run. Every role has an explicit **definition of done** in its agent/skill file — a run isn't done until those boxes are ticked and reported.

## Active initiative: Contract field extraction (spec finalized, build not started)

Requirement: `docs/contract_extraction.md`. Adds an operator-facing **field-extraction** layer on top of the existing visual document extractor — upload a contract, pick fields, get a strict 10-key JSON, persist a row, browse the table, and verify failures by hand.

Skills define the whole thing — **load them before touching this feature**:
- `.claude/skills/contract-field-extraction/SKILL.md` — the binding spec: field catalogue, 10-key JSON contract, grounding rules, the failure/verification model, backend module layout, API surface, DB table, frontend behaviour, tests, definition of done.
- `.claude/skills/contract-extraction-orchestrator/SKILL.md` — the 4-phase build workflow; `contract-extraction-builder` implements, `contract-extraction-grader` verifies with a regression-gated rubric, max 3 rounds per phase plus no-progress and regression stops.

Decisions confirmed by Pradeep (2026-08-26), binding:
- **The schema is exactly 10 fields, no larger catalogue.** Default-selected 5: `contract_title`, `customer`, `effective_date`, `term_end_date`, `contract_value`. The other 5: `governing_law`, `payment_terms`, `notice_period`, `renewal_terms`, `termination_clause`.
- **All 10 are individually selectable and deselectable (revised 2026-08-27, supersedes the "fixed 5" rule).** The first five are only the picker's *default* selection — every one can be moved out. A valid selection is any **non-empty** subset of the 10: one field is enough, and it is extracted while the other nine come back blank. An **empty selection is a 422**, and the UI disables Extract before it can be submitted. Requested = exactly what was selected; nothing is implicit.
- **New route + new module**, not an extension of the existing one: `frontend/app/(protected)/contract-extraction/` and `backend/app/contract_fields/` + `backend/app/api/routes/contract_extractions.py` (`/api/v1/contract-extractions`).
- **Storage**: one new table `contract_field_extraction` in the **existing** Dockerized Postgres (`db` service, host 5434) — no second container.
- **Table shape**: **10 real named columns**, one per field, `NOT NULL DEFAULT ''` — the table maps one-to-one onto the JSON (10 keys, 10 columns, same names). No name/value pairs, no JSON blob for the optional half. Plus `selected_fields` (JSON) so a blank that was never requested is distinguishable from one that was extracted and not found.
- **A blank requested field is a failure requiring human verification.** Requested = exactly the fields the operator selected. **One** blank requested field sets `extraction_status = needs_verification`, lists the keys and reasons in `unresolved_fields`, and surfaces the record in the UI behind a non-dismissible banner plus a verification view beside the document. A blank in an **unselected** optional field is expected and never a failure. A `needs_verification` result still persists and still returns 200 — it is a business outcome, not a transport error. Human corrections go to `verified_values`; the 10 machine columns are never overwritten, mirroring how the existing pipeline keeps review corrections separate from parser text.

**Non-disruption is the top constraint.** `backend/app/visual_document_extractor/**`, `backend/app/api/routes/document_extractions.py`, `frontend/components/document-extractions/**`, the legacy OCR modules, and all existing tables are **read-only** for this work. The verification layer *extends* the existing pipeline's review vocabulary (`PageStatus`, `ReviewStatus`, `ReviewState`, `AuditEvent`) by importing and mirroring it in the new module — never by editing that package. The only shared files that may change: `api/main.py` (one router line), `models.py` (append table), `core/config.py` (append settings), one Alembic revision, `middleware.ts`, the nav component, and the regenerated client. Needing more means reporting BLOCKED.

**Blank beats a guess:** a field that can't be grounded in extracted elements or normalized is `""` — never `null`, never a missing key, never an invented value. The JSON always carries **the same 10 keys in the same order**, whatever the operator selected; the key set is static, so no placeholder slot names are ever needed. Blank is still never a guess — it is now an outcome that raises the record for a human rather than passing quietly.

**Status (2026-08-27):** All 4 phases built. Phase 1 **PASS 92**, Phase 2 **PASS 91**, Phase 3 **89, all four gates pass**; Phase 4 (frontend) built but **never graded**. Backend suite: 445 passed, 25 skipped; frontend Playwright 5 passed; tsc/biome/ruff/mypy clean. Nothing committed — all in the working tree.

Migrations applied to the local Docker Postgres: `e7f8a9b0c1d2` (create table), then `b9c0d1e2f3a4` (rename `selected_optional_fields` → `selected_fields` and backfill pre-existing rows with the five formerly-implicit keys, so their recorded scope still matches how they were extracted).

Changes made after Phase 4, at Pradeep's request:
1. **JSON panel shows verified values.** The panel read the machine columns, so an approved human correction still displayed `""` and stayed flagged as a failure. It now renders *effective* values (verified where present), Copy JSON matches, and "View details" gained a Human verification section showing human and machine value side by side. The 10 machine columns are still never overwritten.
2. **Dual-list field picker** (`field-transfer.tsx`) replaced the combobox: available left, selected right, move one or the whole set either way. `field-combobox.tsx` was deleted.
3. **The "fixed 5" rule was reversed** — see the schema bullets above.

**Running the app:** `docker compose up -d --wait` brings up db + backend + frontend, all healthy, with migrations and superuser seeding done. Ports 3000/8000/5434 must be free.

**Fixed 2026-08-27 (was the deferred blocker list):**
1. ~~**Numbered clauses blank the field.**~~ **Fixed.** `REJECTED_SENSITIVE_MISMATCH` removed from `NEVER_OVERRIDABLE` in `grounding.py`, so gate 2 gets to re-apply the sensitive comparison at *span* scope — where dropping a clause number is not a changed number, but altering a number still is. `REJECTED_INVALID_REFERENCE` and `REJECTED_OVERLAP` stay un-overridable. Regression tests cover `8.`, `8.1`, `8.1.2`, `(a)`, `Article 8.`, `Section 12 -`, plus adversarial cases proving an altered or negated value is still refused.
2. ~~**Label fragments (`"Terms:"`, `"Clause:"`) stored as values.**~~ **Fixed.** Three distinct causes, all in `extractor.py`:
   - `_earliest_label` took the earliest-starting match and stopped mid-label when two patterns describe the same label with different extents (`auto…renew\w*` = "Automatic Renewal" vs `renewal\s+terms?` = "Renewal Terms"). It now extends the span through any *overlapping* match, consuming the label whole. Disjoint later matches are still not absorbed, so `"Termination: Termination for convenience"` keeps its value.
   - **Word-level OCR was the real trigger.** Tesseract emits one element *per word*, so `"Renewal"` and `"Terms:"` are separate elements and the bare-heading branch returned the rest of the label as the value. That branch now absorbs label continuations and gathers the clause across elements; new `_label_across_elements` handles the case where the label itself is split so no single element matches it at all (`"Notice"` + `"Period:"`).
   - Pass ordering: in-element label+value → cross-element read → bare-heading follow-on. A loose value-shaped pattern (`\binvoice\b`) matching mid-clause used to pre-empt the good candidate and return `"date."`.

   Two boundary bugs found while fixing this, both one character wide: citing the label's own trailing token (`"Law:"` for `"State of Delaware"`) made gate 1 reject a correct value, and letting that token count as the clause's first word truncated the result. Clause gathering also has to test the *joined remainder* for the next heading, not a lone token — headings are word-split too, or the clause runs on into the following fields.

**Customer replaces `parties` (2026-08-28, Pradeep):** the field records the **counterparty** — one organisation, the side that is not the deployment's own. The home organisation is configuration: `settings.CONTRACT_HOME_ORGANIZATIONS`, a **list** (legal names contain commas), default `["Acme Corp, Inc."]`, overridable as JSON in the environment. This removes "how many parties are there" from the extraction path. Migration `c1d2e3f4a5b6` renames the column `parties` → `customer`; existing rows are renamed, not rewritten, because stripping the home name out of stored text in SQL would be a guess. Matching ignores case, punctuation, and the corporate suffix, and never matches inside a longer word. More than one candidate organisation is `""` and a human check — never a guess between them.

**Modal routing fixed (2026-08-28).** `ContractFieldService` called `DocumentExtractionService.ingest()` directly — the **local** router, whose only installed adapter is tesseract — while the existing `/document-extractions` upload hands work to `ModalExtractionCoordinator` when Modal is configured. That is why a text-perfect PDF came back as OCR (`Net 30` → `Net 3@`): it was rasterised and OCR'd despite having a 1037-character native text layer, because every *primary* adapter (docling, paddleocr, mineru, marker) reports "Optional dependency not installed" in this image and routing falls back to the secondary.

`service._ingest()` now builds the same coordinator against its own injected extraction service (the route's `get_modal_coordinator()` is hard-wired to the global one, so it cannot be reused without discarding the injected service and any test double) and gates it on the same five settings. `submit()` is **asynchronous** — it returns a QUEUED document with no elements — so `_ingest` waits for the pages to settle, using the same rule the Modal callback applies (no page `PENDING` or `EXTRACTING`). Bounded by `CONTRACT_EXTRACTION_MODAL_WAIT_SECONDS` (90s) / `CONTRACT_EXTRACTION_MODAL_POLL_SECONDS` (2s). On timeout the partial document is used, a warning is attached, and the row persists as `needs_verification` — never a second, separately billed local extraction for the same upload. `submit()` already falls back to local `ingest` itself when dispatch fails, so that case never reaches the wait.

**⚠️ Modal cannot work locally as configured.** The Modal endpoint is live (401 auth challenge), but `DOCUMENT_EXTRACTOR_PUBLIC_BASE_URL` is an expired `trycloudflare.com` quick tunnel whose DNS no longer resolves — Modal cannot fetch the source back, so dispatch fails and every local extraction falls back to tesseract. Refresh that tunnel URL to exercise Modal locally. On Render it is a real, permanently reachable URL.

**Block-element run-on fixed (2026-08-28, found on Render).** Once extraction went through Modal, a *digital* parser returned a whole labelled block as **one element** — "Governing Law: … \n Payment Terms: … \n Notice Period: …" — and `_after_label` took everything to the end of it, so each field swallowed the clauses after it (`governing_law` came back as the entire rest of the contract). Word-level OCR had hidden the whole class: there was never more than one clause in an element to run into. `_after_label` now stops at the next field's label, matched from the anchored heading forms so only a *labelled* boundary cuts — prose mentioning "termination" survives, "Termination Clause:" ends the value. Covered both for newline-separated and single-line blocks.

**Still open:**
3. Residual carve-out phrasings outside the `_NEGATION` blacklist (`to the extent that`, `so long as`, `only if`, `apart from`, `with the exception of`, bare `save`) let a truncated excerpt through. Verbatim source text, not an invention; lands as `NEEDS_REVIEW`. Cheap to add those tokens; do not chase exhaustiveness.
4. `UnresolvedField.detail` is always `None` over the wire — the specific reason text lives only in `warnings`, so the UI's per-row reason shows the bare enum.
5. `customer` comes back blank on the scanned samples — the preamble patterns do not survive word-level OCR (the preamble arrives as one element per word). Same class as the fixed label-split problem, not yet addressed.
6. **The LLM path is non-deterministic on scanned documents.** Identical input, identical code, two runs: `effective_date` `''` then `15/01/2026`. The deterministic pass cannot read word-split dates, so it falls through to the provider, whose proposals sometimes ground and sometimes do not. Not a regression — inherent to leaning on the model for these fields.

**Note:** the `OPENAI_API_KEY` in `.env` is **live again** (confirmed `200 OK` from `/v1/chat/completions`), so the LLM extraction path is real and billable. `test_api.py` was making 10 live calls per run; it now stubs `extract_with_provider` (suite runtime 7.9s → 0.21s, zero outbound traffic).

**⚠️ `.env` points `POSTGRES_SERVER` at a remote Render Postgres.** A plain `alembic upgrade head` in this repo applies DDL to that remote database, not the local Docker one. For local work pass `POSTGRES_SERVER=localhost POSTGRES_PORT=5434` (env vars override `.env`), which is how the migration was applied.

## House rules
- Don't start servers with `dangerouslyDisableSandbox` unless a command genuinely needs network/ports.
- Keep generated client (`frontend/src/client/`) regenerated, never hand-edited.
- New backend routes: follow the pattern in `backend/app/api/routes/blog.py` (router prefix + tags, `SessionDep`, register in `api/main.py`).
- New frontend pages: App Router under `frontend/app/`, public pages outside `(protected)/` so middleware doesn't block them. The profile page and its chat must be public (no login required).
