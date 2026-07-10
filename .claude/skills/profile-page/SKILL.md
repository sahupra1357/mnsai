---
name: profile-page
description: How to build and evolve the mnsAI homepage profile/portfolio page — sections, components, content model, and design rules. Use whenever editing frontend/app/page.tsx or components/profile/*.
---

# Profile Page (Homepage)

Rebuild `frontend/app/page.tsx` as a professional profile page for **Pradeep Sahu** — an AI engineer specializing in Generative AI and multi-agent systems, offering project services. The audience is prospective customers and collaborators deciding whether to engage him. Every section should answer: *what can he do for me, and what proof is there?*

**Content source:** all copy comes from `docs/profile-draft.md` (derived from `docs/resume.md`). Never invent facts; omit anything marked `[NEEDS INPUT]` rather than stubbing placeholder data.

**Frozen v1 draft:** the first draft lives at `frontend/app/drafts/profile-v1/` (own `_components/` copies — fully self-contained) and is linked from the nav Resources dropdown for side-by-side comparison. **Never edit anything under `app/drafts/profile-v1/`**; the v2 rebuild may freely rewrite `components/profile/*` and `lib/profile-data.ts` because v1 no longer depends on them.

**Original product landing backup:** `frontend/app/_archive/product-landing.tsx` — never edit or delete.

## Design direction v2 — "evidence-driven dossier"

The v1 draft (see `/drafts/profile-v1`) was correct but generic — a standard marketing landing with uniform card grids. v2 replaces that with an **editorial, case-study feel**: the page should read like a well-typeset dossier that proves competence, not a template that claims it. Format inspiration (structure only — **do not copy** its colors, copy, or layout verbatim): long-form case-study pages with narrow reading columns, sticky section nav, big stat tiles, and numbered narrative lists.

**Before implementing, load the `frontend-design` skill** for typography/craft guidance.

Core moves:

1. **Editorial layout.** Main content in a narrow reading column (`max-w-3xl`) instead of full-width `max-w-6xl` grids. On `xl+`, a slim sticky section rail (left) with scrollspy highlighting and a pinned "Ask my AI assistant" CTA; hidden below `xl`.
2. **Typography-led hero.** No boxed hero card. Small-caps `ui-main` eyebrow ("AI ENGINEER — GENERATIVE AI & MULTI-AGENT SYSTEMS"), then the name huge and tight (`text-5xl/6xl font-extrabold tracking-tight`), then the value-prop as a large muted dek, then a byline-style row of credential chips (MS + 3 certs). Subtle dot-grid background texture behind the hero only (CSS radial-gradient dots at low opacity, theme-aware).
3. **Proof tiles.** A 4-up band of stat tiles (big `ui-main` number + small muted label), e.g. "3 — Live AI demos on this site", "4 — Certifications", "3 — Cloud platforms", "6 — Agent frameworks". **Every number must be countable from `docs/profile-draft.md`** — no invented metrics.
4. **Question-form section headings.** Sections read as answers: "What can I build for you?", "What have I actually shipped?", "What's in the toolbox?", "How do we start?". Left-aligned, editorial scale (`text-3xl font-bold tracking-tight`), not centered marketing headers.
5. **Services as numbered editorial blocks.** Big muted ordinal (01–04) + bold offer name + description + "Discuss this →" chat-prefill link. Stacked list, not uniform cards.
6. **Experience highlights as a numbered narrative list.** Bold lead-in phrase then plain text (e.g. "**Drone-vision pipelines.** Detected structural corrosion…"). This is the proof spine of the page.
7. **Skills as compact definition lists.** Two-column (mobile: one) group blocks with a small icon + group name + comma-separated or tight-list items. Less card chrome, more typography.
8. **Live demos keep cards** (they're products) but with a consistent "Live demo →" affordance and built-with note.
9. **Both themes intentional.** The site has a theme toggle; verify the page looks designed (not merely inverted) in light *and* dark.
10. **Keep**: `ui-main` blue (#004AAD) as the only accent, shadcn primitives, lucide icons, floating chat launcher bottom-right, footer, `WithSubnavigation` nav.

Anti-goals: no teal/purple palette drift, no copied copywriting from any reference, no fake avatars/headshots, no proficiency percentages, no dense card-grid-everything.

## Page structure (top to bottom)

1. **Nav** — keep `WithSubnavigation` (login, solutions, drafts links intact).
2. **Hero** — per design move 2, with primary CTA "Ask my AI assistant" (scrolls to chat) and secondary "Contact" (mailto).
3. **Proof tiles** — design move 3.
4. **Services** ("What can I build for you?") — design move 5, chat pre-fill per card from the draft.
5. **Experience highlights** ("What have I actually shipped?") — design move 6.
6. **Live demos** — existing solutions (Data Extraction, Course Search, ATS Resume Matcher) as portfolio cards with live links.
7. **Skills** ("What's in the toolbox?") — design move 7, five groups from the draft.
8. **Chat section** ("Ask anything about my experience") — embedded panel (UI stub until the chat-agent phase) + floating launcher.
9. **Contact band** ("Have a project in mind?") — email + LinkedIn from the draft.
10. **Footer** — keep.

## Content model

- All profile copy (name, title, skill groups, services, stats, highlights, project cards, links, **and section headings/subtitles**) lives in one typed data file: `frontend/lib/profile-data.ts`. Components render from it; no copy hard-coded inside JSX — v1 was dinged for hard-coded section headings, don't repeat that.
- The same facts must exist in the agent's documents (`backend/app/profile_agent/docs/`) — when updating one, update the other.

## Components

Place under `frontend/components/profile/` (rewrite freely — v1 has its own frozen copies):
- `hero.tsx`, `proof-tiles.tsx`, `services.tsx`, `highlights.tsx`, `skills-grid.tsx`, `projects-showcase.tsx`, `contact-band.tsx`, `section-rail.tsx`
- `chat-box.tsx` + `chat-launcher.tsx` + `chat-prefill-link.tsx` (client components — see `profile-chat-agent` skill)
- Page itself stays a server component; only chat pieces and the scrollspy rail need `"use client"`.

## Design rules

- Mobile-first: reading column is naturally responsive; rail hidden below `xl`; tiles collapse 4→2→1; floating launcher stays.
- The page is **public** — it must not be added to `middleware.ts` protected paths, and the chat must work logged-out.
- Keep the existing platform pages reachable (login/signup buttons stay in nav even though the hero CTAs change).
- Verify visually with the gstack browse tool (screenshot light + dark, desktop + mobile) before declaring done.
