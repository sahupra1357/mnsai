---
name: profile-page
description: How to build and evolve the mnsAI homepage profile/portfolio page — sections, components, content model, and design rules. Use whenever editing frontend/app/page.tsx or components/profile/*.
---

# Profile Page (Homepage)

`frontend/app/page.tsx` is a professional profile page for **Pradeep Sahu** — an AI engineer specializing in Generative AI and multi-agent systems, offering project services. The audience is prospective customers and collaborators deciding whether to engage him.

**Content source:** all copy comes from `docs/profile-draft.md` (derived from `docs/resume.md`). Never invent facts. Where the v3 structure calls for content that doesn't exist yet (see the placeholder rule below), render an explicit **blank placeholder**, never fabricated data.

**Frozen drafts & backups (never edit anything under these paths):**
- `frontend/app/_archive/product-landing.tsx` — original product landing.
- `frontend/app/drafts/profile-v1/` — 1st draft (generic card-grid), routed at `/drafts/profile-v1`.
- `frontend/app/drafts/profile-v2/` — 2nd draft ("evidence-driven dossier"), routed at `/drafts/profile-v2`.
Both drafts are self-contained (`_components/` copies) and linked from the nav Resources dropdown; the live rebuild may freely rewrite `components/profile/*` and `lib/profile-data.ts`.

## Design direction v3 — reference-format portfolio

v3 mirrors the **format/structure** of a specific reference portfolio homepage (a personal AI-engineer portfolio: avatar hero → work experience dossiers → projects grid → social proof → skills → education/certifications → contact). Screenshots of the reference are in the session scratchpad (`v3ref-*.png`) if present; otherwise follow this spec — it is complete.

**Hard rules — format only:**
- **DO NOT COPY any content** from the reference: no phrases, names, numbers, logos, or copy. Structure, layout patterns, and component shapes only.
- Do not copy its palette either. The page uses the **"Teal & warm paper"** palette (user-chosen, July 2026) — see "Color system" below; keep shadcn primitives, lucide icons, and the existing dot-grid utility.

## Color system — "Teal & warm paper"

Implemented at the token layer (shadcn CSS variables in `app/globals.css` light + dark blocks, plus tailwind accent utilities) so the whole site stays coherent — do not hand-color individual app components outside the profile page.

- **Light theme**: warm off-white/cream paper background (a warm hue, not pure white — think `hsl(40 30% 97%)` territory), soft sand/warm-tinted card surfaces, warm dark-gray text; accent is a **deep teal** (~`hsl(180 70% 25%)` range) with hero/launcher gradients running **teal → cyan**; dot grid and borders warm-tinted.
- **Dark theme**: deep **blue-slate** background (not pure black), slightly lighter slate cards, **bright aqua** accent (readable AA on the dark bg) with the same teal→cyan gradient family glowing brighter; not a flat inversion — surfaces and accent luminosity tuned separately.
- The `ui-main` utility and shadcn `--primary` tokens move to the teal family so nav links, buttons, and focus rings follow; verify AA contrast for body text and accent-on-surface in BOTH themes.
- Status/semantic colors (destructive, success) stay as-is.
- **Placeholder rule:** if a structural slot has no approved content (e.g. employer names, testimonials, press logos, social posts, headshot), render a visible blank placeholder — a dashed-border card/slot with a muted label like "Coming soon" — driven by an EMPTY array/null in `profile-data.ts`, so filling it later means adding data, not code. Never invent content to fill a slot; never silently drop the section.

## Page structure (top to bottom)

1. **Nav** — keep `WithSubnavigation` (Product/Solutions/Resources dropdowns, drafts links, auth buttons intact).
2. **Hero** — two-column: left, a large circular avatar (see "Headshot" below — an initials "PS" ring until a headshot is uploaded); right, a small greeting line ("Hi, I'm Pradeep Sahu"), then a huge headline of the professional title with a blue gradient treatment, then 1–2 bold descriptor lines from the value proposition, then a row of small pill chips (role descriptors from the draft). Below: an "As featured in" slot — **blank placeholder** (no press yet). Dot-grid hero background, subtle gradient wash, theme-aware.
3. **Work Experience** — H2 with a small icon tile. Entry format: org logo slot + org name + location line, role title in accent color, date range line, short summary paragraph, bullet list of accomplishments; optional client-logo strip and testimonial quote card per entry. Content: the resume has **no employer names/dates**, so render ONE placeholder entry (dashed card, "Experience details coming soon") PLUS a "Selected work" sub-block that lists the five approved experience highlights as accomplishment bullets without attribution. The featured-project panel slot (big card with icon, title, description, icon-bullet list, right-hand column of 2–3 stat tiles) IS renderable: use the proof-tile numbers from the draft.
4. **Projects** — H2 grid (2-col on lg): the three live demos as project cards — title, status badge ("Live demo"), description, tech-stack chips, footer link to the running tool. Plus one wider intro panel describing this platform itself (the profile + chat agent system) as a working project, with the chat agent linked — facts only from the draft/repo. Additional project-card slots: none — do not pad with placeholders here, the grid just has 4 items.
5. **Sharing / social proof** — H2 with 2-col card slots for posts/talks. No approved content → the section renders with 2 blank placeholder cards ("Posts and talks coming soon").
6. **Skills** — H2 with the five draft groups as subsections, items as chip clusters (not checklists). Skills come **before** education & certifications: the capability story leads, credentials back it up.
7. **Education & Certifications** — two columns side by side. Education: one card (year slot blank, institution, degree from the draft). Certifications: stacked rows — the 3 certifications (year slots blank, issuer names from the draft).
8. **Let's talk** — contact band: heading, email button, LinkedIn button (from the draft); GitHub slot omitted until provided.
9. **Footer** — keep.

There is **no in-page chat section** — the chat exists ONLY as the floating widget below. Any element that previously deep-linked to `#chat` (featured panel, projects panel) must open the floating widget instead (reuse the prefill event).

## Floating chat widget (the only chat surface)

Format modeled on a messenger-style popover (structure only, wording ours from `profile-data.ts`):
- **Launcher**: fixed bottom-right circular accent button; toggles to an X when the panel is open. Always present while scrolling.
- **Panel**: popover anchored above the launcher, ~380px wide, rounded-2xl, elevated shadow; full-width/height sheet on mobile. Structure top→bottom:
  1. Header row: avatar slot (PS-initials ring until a headshot exists) + name + one-line tagline (e.g. "Ask me about my experience" — take copy from the draft's chat section).
  2. Assistant greeting bubble shown on open (short welcome inviting questions — copy in `profile-data.ts`).
  3. Starter chips (3–4, small pill buttons with icons; include a Contact chip) — clicking sends/prefills that question. Reuse the existing chip + prefill event mechanics.
  4. Scrollable message list (existing streaming rendering).
  5. Footer input bar: text input ("Type your question…" placeholder from data) + send icon button.
- **Behavior**: keep ALL existing chat mechanics — SSE streaming via `/api/profile-chat`, history cap, error toast, prefill events. Restyle/move allowed; breaking the streaming or security wiring is not.

## Left rail — "On this page"

Sticky left navigation on `xl+` (hidden below): a small-caps muted label ("On this page"), then numbered entries (`01`, `02`, …) for the main content sections (work experience, projects, sharing, skills, education & certifications, contact — labels from `profile-data.ts`). Scrollspy: the in-view section's entry is emphasized (bold + accent left bar); entries smooth-scroll to their section anchors. Client component; reuse the scrollspy approach from the frozen v2 draft's `section-rail.tsx` (copy the technique, the draft itself stays untouched).

## Headshot (hero avatar)

The headshot is **uploaded data, not code** — Pradeep manages it at `/settings` → "Profile photo" (superuser-only tab, `components/user-settings/profile-photo.tsx`). Do not reintroduce a hard-coded image path or remove this wiring when rebuilding the hero:

- Bytes live in the DB (`ProfileImage` table, slot `"headshot"`), served by `backend/app/api/routes/profile_image.py`: public `GET /api/v1/profile/image` + `GET /api/v1/profile/image/meta`, superuser-only `POST`/`DELETE`. Uploads are validated by magic bytes (JPEG/PNG/WebP, ≤5 MB) — never by the client-supplied content type.
- `Hero` is an **async server component**: it calls `getProfileHeadshotUrl()` from `lib/profile-image.ts`, which reads `/meta` and returns a `?v=<updated_at>` cache-busted proxy URL, or `null`. Resolving server-side is what keeps a missing photo from rendering as a broken `<img>`.
- Fallback order: uploaded photo → the static `profile.headshot` path → the "PS" initials ring. The initials ring stays the placeholder per the placeholder rule.

## Content model

- ALL copy — headings, labels, chips, placeholder labels included — lives in `frontend/lib/profile-data.ts` (typed). Components render from it; nothing hard-coded in JSX. Empty arrays/nulls drive placeholder rendering.
- The same facts must exist in the agent's documents (`backend/app/profile_agent/docs/`) — when updating one, update the other.

## Components

Place under `frontend/components/profile/` (rewrite freely — drafts have their own frozen copies):
- `hero.tsx`, `experience.tsx`, `featured-panel.tsx`, `projects-grid.tsx`, `sharing.tsx`, `education-certs.tsx`, `skills-chips.tsx`, `contact-band.tsx`, `placeholder-card.tsx`, `section-heading.tsx`, `page-rail.tsx` (On-this-page scrollspy)
- `chat-widget.tsx` (launcher + popover panel, built from the existing `chat-box.tsx`/`chat-launcher.tsx`/`chat-prefill-link.tsx` mechanics) — **do not break** the streaming via `/api/profile-chat`, chips, or prefill events.
- Page stays a server component; only chat pieces and the scrollspy rail are client components.

## Design rules

- Wide content container (~`max-w-6xl`) with generous vertical rhythm between H2 sections; card-heavy layout with rounded borders (`rounded-xl border`), small icon tiles beside H2s, chips everywhere for compact metadata.
- Mobile-first: 2-col grids collapse to 1; hero stacks avatar above text; floating launcher stays.
- Both themes intentional (site has a theme toggle) — dot grid and gradients must read correctly in light and dark.
- The page is **public** — never added to `middleware.ts` protected paths; chat works logged-out.
- Verify visually with the gstack browse binary (light + dark, desktop + mobile) before declaring done.
