# mnsAI — Project Instructions

Full-stack app: FastAPI backend + Next.js 15 (App Router) frontend.

## Run locally
```bash
cd frontend && npm run dev            # Next.js on :3000
docker compose up -d                  # backend + db (FastAPI on :8000)
```

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

## House rules
- Don't start servers with `dangerouslyDisableSandbox` unless a command genuinely needs network/ports.
- Keep generated client (`frontend/src/client/`) regenerated, never hand-edited.
- New backend routes: follow the pattern in `backend/app/api/routes/blog.py` (router prefix + tags, `SessionDep`, register in `api/main.py`).
- New frontend pages: App Router under `frontend/app/`, public pages outside `(protected)/` so middleware doesn't block them. The profile page and its chat must be public (no login required).
