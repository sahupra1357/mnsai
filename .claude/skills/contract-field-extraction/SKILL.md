---
name: contract-field-extraction
description: Spec for the contract field-extraction feature — a fixed 10-field contract schema (all 10 individually selectable, 5 selected by default) extracted to a stable 10-key JSON, persisted to a 10-column relational table, reviewed in a document-left / JSON-right workspace. Use whenever working on backend/app/contract_fields/*, the /contract-extraction page, or its DB table.
---

# Contract field extraction

A **new, additive** capability layered on top of the existing visual document
extractor. The operator uploads a contract, chooses which fields to pull, and gets a
strict 10-key JSON plus a row in a relational table.

Source requirement: `docs/contract_extraction.md`. Decisions below that the requirement
left open were confirmed by Pradeep on 2026-08-26 and are binding.

## Non-negotiable: do not disturb what exists

The existing pipeline is in production shape and stays untouched in behaviour. Treat
these as **read-only**; import them, never edit them:

- `backend/app/visual_document_extractor/**` — intake, classification, routing,
  adapters, execution, semantic, store, preview, modal.
- `backend/app/api/routes/document_extractions.py` and its `/api/v1/document-extractions`
  contract, including `/capabilities`, `/programmatic`, `/modal-jobs`, API keys.
- `backend/app/gptocr/**`, `backend/app/tesractopenaiapi/**`, and the legacy
  `extractorg.py` / `extractorgpt.py` / `extractorts.py` routes.
- `frontend/app/(protected)/document-extractions/page.tsx` and
  `frontend/components/document-extractions/**` — the review workspace keeps working
  exactly as it does today.
- Existing tables: `document_extraction`, `document_preview_artifact`,
  `document_extraction_job`, `document_job_token`, `document_extraction_api_key`.

Allowed edits outside the new module, and nothing more:
- `backend/app/api/main.py` — one `include_router` line.
- `backend/app/models.py` — append the new table model.
- `backend/app/core/config.py` — append new settings.
- one new Alembic revision.
- `frontend/middleware.ts` — add `/contract-extraction` to `PROTECTED_PATHS`.
- `frontend/components/common/with-subnavigation.tsx` — one nav entry.
- `frontend/src/client/` — regenerate, never hand-edit.

If a change appears to require editing a read-only path, stop and report BLOCKED.

## The field catalogue

### Default-selected fields (the picker starts with these five on the right)

**Superseded rule (2026-08-26 → 2026-08-27):** these five used to be *fixed* — always
extracted, never deselectable. Pradeep reversed that on 2026-08-27. **Every one of the
ten fields is now individually selectable and deselectable.** These five are simply the
picker's default selection; a selection that omits all five is valid and is extracted
exactly as asked.

| # | key | meaning | normalization |
|---|-----|---------|---------------|
| 1 | `contract_title` | the agreement's title as written | verbatim, trimmed |
| 2 | `parties` | the contracting parties | **never split or merged** — see below |
| 3 | `effective_date` | date the contract takes effect | `DD/MM/YYYY` |
| 4 | `term_end_date` | expiry / end of term | `DD/MM/YYYY` |
| 5 | `contract_value` | total consideration | `"<CURRENCY> <amount>"`, scale words **expanded** |

### Normalization rules confirmed by Pradeep (2026-08-26) — these override any
### earlier guidance and any grader feedback to the contrary

**Parties — the normalizer never splits.** Whatever the extractor produced as a party
value is **one element**, taken as-is. `"Smith and Wesson"` is one party named
"Smith and Wesson", not two. The normalizer only collapses whitespace; it must never
split on `and`, `&`, or a comma, and never merge or de-duplicate. Deciding how many
parties a contract has is the **extractor's** job in Phase 3 (it delimits them from
the source elements), not the normalizer's. When the extractor yields several parties,
join them with `"; "` in source order; when it yields one, emit that one unchanged.
This removes the whole guessing problem from `normalize.py` — there is nothing left
for it to get wrong.

**Dates — `DD/MM/YYYY`.** Not ISO. `15 January 2026` → `"15/01/2026"`. Input that is
genuinely ambiguous is still refused: a bare `01/02/2026` cannot be told apart from
1 Feb and 2 Jan, so it stays `""` with a warning. Impossible dates (`2026-02-30`),
two-digit years, and multi-date spans stay `""`.
*Consequence to respect:* the DB column holds `DD/MM/YYYY` **text**, so a SQL
`ORDER BY` on it is lexical, not chronological. Do not offer or imply chronological
sorting on date columns in the table view.

**Currency — expand scale words, do not blank them.** `"$2 million"` →
`"USD 2000000.00"`, `"$1.5 million"` → `"USD 1500000.00"`, `"$250k"` →
`"USD 250000.00"`, `"EUR 3.2m"` → `"EUR 3200000.00"`. Recognized scales: `k`/`thousand`,
`m`/`mm`/`million`, `bn`/`b`/`billion`. Silently dropping the scale is the defect —
`"$2 billion"` must never become `"USD 2.00"`. What stays `""`: a bare number with no
currency, an unrecognized scale token, two conflicting amounts in one string, and any
value whose locale reading is genuinely ambiguous (`USD 1.500`).

### The other five (the picker starts with these on the left)

| # | key | meaning | normalization |
|---|-----|---------|---------------|
| 6 | `governing_law` | governing law / jurisdiction | verbatim, trimmed |
| 7 | `payment_terms` | payment schedule or terms | verbatim, trimmed |
| 8 | `notice_period` | notice required to terminate | verbatim, trimmed |
| 9 | `renewal_terms` | renewal / auto-renewal terms | verbatim, trimmed |
| 10 | `termination_clause` | grounds and mechanics of termination | verbatim, trimmed |

**The schema is exactly these 10 fields — there is no larger catalogue to pick from.**
All 10 are individually toggleable. A valid selection is **any non-empty subset of the
10**: one field, five, ten, or any mix. An **empty selection is a 422** — there would be
nothing to extract; the UI disables Extract before it can be submitted. An unselected
field is simply not extracted and its value is `""` — its **key still appears**, because
the key set never changes.

This schema is a single source of truth defined **once** in the backend
(`backend/app/contract_fields/catalogue.py`) and served to the frontend by
`GET /api/v1/contract-extractions/fields`. The frontend never hardcodes a second copy.

Each catalogue entry carries: `key`, `label`, `description`, `value_format`, and
`default_selected: bool` (whether the picker starts with it selected — a starting point,
never a lock). The description is the prompt-facing definition — extraction quality
comes from this file, so it is the file to tune.

## The 10-key JSON contract

The result payload always has **exactly the same 10 keys**, always in catalogue order:
the 5 default-selected keys, then the other 5. The key set is **static** — it does not vary
with what the operator selected, so no placeholder or slot naming is ever needed. Every
value is a **string**; a field that was not selected, not found, or not groundable is
`""`. Never `null`, never a missing key, never an invented value.

```json
{
  "contract_title": "Master Services Agreement",
  "parties": "Acme Corp; Northwind Ltd",
  "effective_date": "15/01/2026",
  "term_end_date": "",
  "contract_value": "USD 250000.00",
  "governing_law": "State of Delaware",
  "payment_terms": "Net 30",
  "notice_period": "",
  "renewal_terms": "",
  "termination_clause": ""
}
```

Above, the operator selected `governing_law` and `payment_terms` only; the other three
optional keys are present and blank. `term_end_date` is blank for the opposite reason —
it was extracted but not found in the document. **Blank alone does not say which case
applies**, which is why `selected_optional_fields` is persisted and returned (below).

The API response wraps this as `{"extraction_id", "document_id", "fields": {...10...},
"selected_optional_fields": [...], "extraction_status", "unresolved_fields": [...],
"field_provenance": [...], "warnings": [...], "verified_values": {...},
"created_at"}`. The right-hand JSON pane renders **`fields` only** — the 10 keys,
nothing else. Provenance, the selection list, and the verification detail live behind a
"View details" affordance, matching the existing workspace's pattern.

## Grounding rules (quality gate)

Field values are derived from content the extractor already produced — this feature
never runs its own OCR.

1. Input is the document's normalized `elements` plus `semantic_result` from
   `DocumentResult` (`backend/app/visual_document_extractor/models.py`).
2. A proposed value must appear in, or be a normalization of, the text of at least one
   source element. Reuse the verification approach in
   `visual_document_extractor/semantic.py` (`verify_candidate`, `GroundingStatus`) —
   import it; do not fork it.
3. Ungrounded, sensitive-mismatch, or overlap-rejected candidates become `""` and add
   a warning. **A blank is always correct; a plausible guess is a defect.**
4. Each non-blank value records provenance: `field_key`, `page_number`,
   `source_element_ids`, `grounding_status`, `confidence`.
5. Dates and amounts that cannot be normalized to the table's format stay `""` with a
   warning naming the raw text — do not emit a half-parsed value. A **scale word is not
   ambiguity**: expand it (see the currency rule above). Dropping it silently, or
   emitting the bare number, is a defect.

## Extraction outcome & human verification

This extends the existing pipeline's review concept to the field layer. It does **not**
relax the grounding rules — a value that cannot be grounded is still `""`, never a
guess. What changes is the **outcome**: a blank in a field the operator actually asked
for is a **failure**, not a quiet pass, and the record is raised for a human.

### Requested fields

**Requested = exactly the fields the operator selected.** Nothing is added implicitly.
Select one field and the failure scope is that one field; select ten and it is all ten.
Unselected fields are **out of scope** — blank there is expected and never counts as a
failure, and this now applies to all ten keys, including the five default-selected ones
when the operator moves them out.

### The failure rule

> If **any single requested field** comes back `""`, the extraction is a **failure**
> and must be surfaced for human verification. One blank is enough — there is no
> partial-credit threshold and no "mostly fine" outcome.

`unresolved_fields` lists every requested key that came back blank, each with the
reason: `not_found`, `ungrounded`, `normalization_failed`, or `provider_unavailable`.
The reason comes from the grounding/normalization step that produced the blank — never
a generic "failed".

### Status model

Mirror the existing pipeline's vocabulary (`PageStatus`, `ReviewStatus`,
`ReviewState` in `visual_document_extractor/models.py`) rather than inventing a
parallel one:

| `extraction_status` | meaning |
|---|---|
| `complete` | every requested field is non-blank; no human action needed |
| `needs_verification` | one or more requested fields blank — **the failure state** |
| `verified` | a human filled in or confirmed the unresolved fields and approved |
| `rejected` | a human judged the extraction unusable |

A `needs_verification` result is still **persisted and still returns HTTP 200** — it is
a business outcome, not a transport error. Never fail the request, never withhold the
row: the row is exactly what the human needs to work from.

### Human corrections stay separate from machine output

The existing pipeline stores review corrections separately from parser text; do the
same here. The 10 field columns hold the **machine-extracted** values and are never
overwritten by a human. Human input goes to `verified_values` (JSON, key → value).
The **effective value** of a field is its verified value if present, otherwise the
machine value; the table view and any export show the effective value and mark which
fields were human-supplied.

Verification is audited: `verified_by` (user id), `verified_at`, and an append-only
`audit_events` list following the existing `AuditEvent` shape.

### Verification endpoint

`PATCH /{extraction_id}/verify`, mirroring `PageReviewRequest`:
`{"action": "save" | "approve" | "reject", "values": {field_key: str}, "note": str|null}`.

- `values` accepts **requested keys only** — a key that was never requested, or an
  unknown key, is 422.
- `approve` requires every `unresolved_fields` entry to have a non-blank effective
  value; otherwise 422 naming the still-blank keys. A human cannot approve a result
  that is still incomplete.
- `save` persists partial work and leaves the status at `needs_verification`.
- `approve` sets `verified`; `reject` sets `rejected`. Both stamp `verified_by` /
  `verified_at` and append an audit event.

## Backend module

New package `backend/app/contract_fields/`:

```
catalogue.py   the 10 field definitions, default-selected flag, key order, the 10-key assembler
models.py      pydantic request/response: FieldSelection, ContractFieldResult, FieldProvenance
extractor.py   elements + semantic_result -> candidates (LLM-assisted, grounded)
grounding.py   thin wrapper over visual_document_extractor.semantic verification
normalize.py   date / currency / party-list normalizers, all total functions returning "" on failure
verification.py requested-field set, unresolved detection + reasons, status transitions
store.py       insert + owner-scoped paged read + verification update of the table
service.py     orchestration: run/reuse extraction -> extract fields -> ground -> normalize
               -> classify outcome -> persist
```

Route file `backend/app/api/routes/contract_extractions.py`, prefix
`/contract-extractions`, tag `contract-extractions`, registered in
`backend/app/api/main.py`. Follow the `blog.py` pattern (`SessionDep`, `CurrentUser`).

| method | path | purpose |
|--------|------|---------|
| `GET` | `/fields` | the 10-field schema plus `default_fields`, the picker's starting 5 |
| `POST` | `""` | multipart upload + `selected_fields` (1–10 keys); returns `ContractFieldResult` |
| `GET` | `/{extraction_id}` | one owner-scoped result |
| `PATCH` | `/{extraction_id}/verify` | save / approve / reject human verification |
| `GET` | `/records` | paged owner-scoped table rows; filterable by `extraction_status` |
| `GET` | `/{extraction_id}/source` | the stored source for the left pane |

Rules: every endpoint owner-scoped via `CurrentUser`; `selected_fields` accepts any
non-empty subset of the 10 keys — an **empty selection**, an unknown key, or a duplicate
is a 422; no key is privileged; the endpoint stays privilege-free — no shell, no fetching, no
writes outside its own table.

**LLM use:** OpenAI SDK via `settings.OPENAI_DEPLOYMENT_ID`, as the rest of the repo
does. The API key in `.env` has been returning 401 — the service must degrade to
deterministic-only extraction and return blanks plus a clear warning rather than 500.
Prompts and provider output never reach the logs.

## Database

One new table in the **existing** Dockerized Postgres (`db` service in
`docker-compose.override.yml`, host port 5434) — no new container, no second
connection. SQLModel model appended to `backend/app/models.py`, one Alembic revision.

`class ContractFieldExtractionRecord(SQLModel, table=True)`,
`__tablename__ = "contract_field_extraction"`:

- `id: uuid` PK
- `owner_id: uuid` FK `user.id`, indexed, `ondelete="CASCADE"`
- `document_id: uuid` — the `document_extraction` row this came from, indexed
- `source_name: str(255)`, `source_sha256: str(64)` indexed
- **10 named field columns**, one per catalogue key, all `str`, `nullable=False`,
  `default=""` — `contract_title`, `parties`, `effective_date`, `term_end_date`,
  `contract_value`, `governing_law`, `payment_terms`, `notice_period`,
  `renewal_terms`, `termination_clause`
- `selected_fields: list` JSON column — which of the ten keys were requested, so a
  blank column can be told apart from a field that was never asked for. Any non-empty
  subset of the ten. (Renamed from `selected_optional_fields` by revision
  `b9c0d1e2f3a4`, which also backfills pre-existing rows with the five formerly-implicit
  keys so their recorded scope still matches how they were extracted.)
- `extraction_status: str` — `complete` | `needs_verification` | `verified` | `rejected`,
  `nullable=False`, indexed (the table view filters on it)
- `unresolved_fields: list` JSON column — requested keys that came back blank, with
  reasons
- `verified_values: dict` JSON column — human-supplied values, kept **separate** from
  the 10 machine columns, which are never overwritten
- `verified_by: uuid | None` FK `user.id`, `verified_at: datetime | None`
- `warnings: list` JSON column, `field_provenance: list` JSON column,
  `audit_events: list` JSON column
- `created_at: datetime`

Because the schema is fixed, the columns are **real named columns** — no
`var_field_N_name`/`_value` pairs and no JSON blob for the optional half. The table maps
one-to-one onto the JSON: 10 keys, 10 columns, same names.

Blank means blank: columns are `NOT NULL DEFAULT ''`, never nullable. Dates are stored
as normalized `DD/MM/YYYY` **strings** so an unparseable source stays representable as
`""` — do not use a `date` column. Because that text is not lexically sortable by
chronology, the table view must not offer date sorting.

Insert happens once, after grounding and normalization, in the same request. A failed
insert fails the request — never return JSON that was not persisted.

## Frontend

New route `frontend/app/(protected)/contract-extraction/page.tsx` plus
`frontend/components/contract-extraction/*`. Add `/contract-extraction` to
`PROTECTED_PATHS` in `middleware.ts`.

**Nav placement (confirmed by Pradeep):** one entry in the **Solutions** dropdown in
`frontend/components/common/with-subnavigation.tsx`, appended to the existing
`children` array — it belongs beside "Data Extraction", which likewise sits at a
top-level path rather than under `/solutions/`:

```ts
{
  label: "Contract Field Extraction",
  subLabel: "Pull 10 key contract fields to JSON, verify blanks, and store the row",
  href: "/contract-extraction",
},
```

That single object is the **only** change permitted in the nav file — do not reorder,
retitle, or restructure the existing entries.

Four states on one route:

1. **Select & upload** — a dropzone (mirror `document-upload.tsx`'s accepted types and
   size messaging) and one **dual-list field picker** (`field-transfer.tsx`) covering
   **exactly the 10 schema fields**. Two lists side by side: unselected fields on the
   **left**, everything being extracted on the **right**. Rows move across individually
   (double-click, or highlight then move) or as a whole set in either direction.

   **Every one of the ten is movable, both ways.** The five `default_selected` fields
   start on the right; that is a starting point, never a lock. The right-hand list may
   be emptied completely, in which case there is nothing to extract and **Extract is
   disabled** (labelled "Select a field to extract"). **One field on the right is
   enough** to proceed — it is extracted and the other nine come back blank.

   Both lists are `role="listbox"` with `aria-multiselectable`; on a row `aria-selected`
   means *highlighted for transfer*, while which list it sits in is what determines
   selection. Each list states its consequence in situ — left, "never extracted,
   returned blank"; right, "a blank in any of these is a failure to verify" — so the
   operator sees what the choice costs before extracting. Keep labels short and
   scannable; descriptions are one truncated line. The count ("7 of 10 fields") is
   visible at all times.

   The starting selection comes from `default_fields` in `GET /fields` and is seeded
   **once**, guarded so a later render never re-adds a field the operator deliberately
   moved out.

   Built from existing primitives — no `cmdk`, no `@radix-ui/react-popover`, no new
   dependency.
2. **Result** — two panes, `lg:grid-cols-2`, stacked on mobile:
   - **left**: the document, reusing the existing `SourceViewer` component as-is
     (import it; do not copy or modify it).
   - **right**: the 10-key JSON, read-only monospace, styled like
     `json-extraction-panel.tsx`. All 10 keys always render, in catalogue order; blank
     values show as `""` — visibly empty, never hidden or collapsed. Unselected fields
     are dimmed or badged "not selected"; **unresolved requested fields are highlighted
     as failures** (destructive-toned, with the reason on the row) so the two kinds of
     blank never look alike. Include a copy-JSON button.
   - **Status banner, above both panes.** `complete` → a quiet success line.
     `needs_verification` → a prominent destructive-toned alert naming the count and the
     failed keys ("3 requested fields could not be extracted — human verification
     required"), with a **"Verify now"** action. The banner is not dismissible while the
     status is `needs_verification`; a failure must never be silently scrollable past.
   - Header actions: **"Open table"**, plus start-over.

3. **Verification** — reachable from the banner, and the reason the document pane
   matters: a checklist of `unresolved_fields`, each with its label, its failure reason,
   and a text input, shown **beside the document** so the human can read the value off
   the source. Machine-extracted fields show read-only for context and are not editable.
   Actions: **Save** (partial, stays `needs_verification`), **Approve** (blocked with an
   inline message until every unresolved field has a value), **Reject** with a note. On
   approve the status becomes `verified` and the banner goes quiet.
4. **Table** — the persisted rows: a shadcn `Table` of all 10 field columns plus
   source name, **status**, and timestamp, horizontally scrollable in its own
   `overflow-x-auto` container, paged from `GET /records`. Reachable from the result
   header and directly at `/contract-extraction/records`. Rows show the **effective**
   value (verified if present, else machine) with human-supplied cells marked, a status
   badge, and a filter for `needs_verification` so a reviewer can find the failures.
   Clicking a row opens its verification view.

Styling follows the house palette ("Teal & warm paper") and existing shadcn primitives
— no new design language. Errors surface in the existing inline alert pattern, not
`alert()`. Every control keyboard-reachable and labelled; the JSON pane gets an
`aria-label`.

Browser calls go through the Next.js proxy (`/api/proxy/api/v1/contract-extractions`)
like `components/document-extractions/api.ts`, or the regenerated OpenAPI client.
Tokens never touch localStorage.

## Tests (part of done, not optional)

- `backend/app/tests/contract_fields/` — schema integrity (exactly 10 keys, unique,
  5 default-selected + 5 not); the assembler (the **same** 10 keys in the same order for
  every selection, including a single-field selection and all-ten); normalizers (valid,
  ambiguous, garbage → `""`); grounding rejection → `""` + warning; **empty selection**,
  unknown key, or duplicate → 422; a formerly-fixed key selected alone → 200 with only
  that key populated; owner isolation on `/records` and `/{id}`; insert-then-read round
  trip proving the 10 columns match the 10 JSON keys.
- **Verification behaviour** — one blank **selected** field → `needs_verification`;
  a blank **unselected** field → still `complete` (the case most likely to regress),
  including a default-selected field the operator moved out; all requested fields
  present → `complete`; `unresolved_fields` carries the right keys and reasons;
  `approve` with a still-blank unresolved field → 422; `approve` when complete →
  `verified`; a verified value never overwrites its machine column; `verify` on another
  owner's record → 404.
- A regression test asserting the existing `/api/v1/document-extractions` responses are
  unchanged.
- Frontend: the five defaults starting on the right and **all** being movable out,
  the empty-right-list case disabling Extract, a one-field selection enabling it,
  moving the whole set both ways, all 10 keys rendering regardless of selection, and
  the failure banner appearing whenever the status is `needs_verification`.

## Definition of done

1. `GET /fields`, `POST ""`, `GET /{id}`, `PATCH /{id}/verify`, `GET /records`,
   `GET /{id}/source` all work owner-scoped.
2. A real upload returns the same 10 string keys for any selection, and writes exactly
   one table row whose 10 field columns match the 10 JSON keys one-to-one.
3. Unavailable values are `""` in both JSON and DB — no nulls, no invented values —
   and `selected_fields` records what was actually requested. An empty selection is
   refused with a 422 rather than silently defaulted.
4. **Any blank requested field yields `needs_verification`**, the row still persists,
   the response is still 200, and the UI shows the non-dismissible failure banner.
   Approve is refused while any unresolved field is still blank, and a human value
   never overwrites a machine column.
5. `/contract-extraction` renders upload → doc-left/JSON-right → verification → table,
   and is auth-guarded.
6. `/document-extractions` and its API are byte-for-byte unchanged in behaviour; its
   tests still pass.
7. New tests pass; `alembic upgrade head` applies cleanly on the Docker DB.
8. The OpenAPI client is regenerated, and lint/typecheck are clean.
