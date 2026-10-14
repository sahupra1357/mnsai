"use client"

import {
  BookOpen,
  ChevronRight,
  ChevronsDownUp,
  ChevronsUpDown,
  Compass,
  type LucideIcon,
  Search,
  Wrench,
  X,
} from "lucide-react"
import Link from "next/link"
import { stageIcon } from "@/components/knowledge/stage-icons"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import type { KDoc, KGroup, KSection } from "@/lib/knowledge/tree"
import type { SolutionStatus } from "@/lib/solutions"
import { cn } from "@/lib/utils"

export type SidebarProject = {
  title: string
  href: string
  status: SolutionStatus
}

type Props = {
  start: KDoc[]
  sections: KSection[]
  projects: SidebarProject[]
  /** Slug of the page being read, if any. */
  activeSlug?: string
  onNavigate?: () => void
}

const STORAGE_KEY = "knowledge-hub.sidebar.v1"

function readOpen(): Set<string> | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    return raw ? new Set(JSON.parse(raw) as string[]) : null
  } catch {
    return null
  }
}

function writeOpen(open: Set<string>) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify([...open]))
  } catch {
    // storage unavailable (private window, blocked) — state just isn't remembered
  }
}

const STATUS_DOT: Record<SolutionStatus, string> = {
  live: "bg-emerald-500",
  demo: "bg-amber-500",
  source: "bg-muted-foreground/40",
}

/**
 * The hub's table of contents. Two levels fold: a stage, and inside it each
 * group (Learn, and every Apply sub-area). Open/closed state is remembered per
 * visitor; the page being read always forces its own stage and group open.
 * Typing in the filter overrides folding and shows every match.
 */
export function KnowledgeSidebar({
  start,
  sections,
  projects,
  activeSlug,
  onNavigate,
}: Props) {
  const activeSection = sections.find(
    (s) =>
      s.overview?.slug === activeSlug ||
      s.groups.some((g) => g.docs.some((d) => d.slug === activeSlug)),
  )
  const activeGroup = activeSection?.groups.find((g) =>
    g.docs.some((d) => d.slug === activeSlug),
  )

  const forced = useMemo(() => {
    const f = new Set<string>()
    if (activeSection) f.add(activeSection.key)
    if (activeSection && activeGroup)
      f.add(`${activeSection.key}::${activeGroup.key}`)
    if (start.some((d) => d.slug === activeSlug)) f.add("start")
    return f
  }, [activeSection, activeGroup, start, activeSlug])

  // Server render and first client render agree on the default; the stored
  // state is applied after mount to avoid a hydration mismatch.
  const [open, setOpen] = useState<Set<string>>(
    () => new Set(["start", ...forced]),
  )
  const [query, setQuery] = useState("")
  const activeRef = useRef<HTMLAnchorElement | null>(null)

  useEffect(() => {
    const stored = readOpen()
    setOpen(new Set([...(stored ?? ["start"]), ...forced]))
  }, [forced])

  useEffect(() => {
    // Scroll only the sidebar's own scroller — scrollIntoView would also
    // scroll the window and push the site nav off-screen.
    const el = activeRef.current
    if (!el) return
    let box: HTMLElement | null = el.parentElement
    while (box && !/(auto|scroll)/.test(getComputedStyle(box).overflowY))
      box = box.parentElement
    if (!box) return
    const r = el.getBoundingClientRect()
    const b = box.getBoundingClientRect()
    if (r.top < b.top || r.bottom > b.bottom)
      box.scrollTop += r.top - b.top - b.height / 2
  }, [activeSlug])

  const toggle = useCallback((key: string) => {
    setOpen((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      writeOpen(next)
      return next
    })
  }, [])

  const allKeys = useMemo(
    () => [
      "start",
      "projects",
      ...sections.flatMap((s) => [
        s.key,
        ...s.groups.map((g) => `${s.key}::${g.key}`),
      ]),
    ],
    [sections],
  )
  const setAll = (expand: boolean) => {
    const next = new Set(expand ? allKeys : [...forced])
    writeOpen(next)
    setOpen(next)
  }

  const q = query.trim().toLowerCase()
  const matches = (d: KDoc) =>
    !q || d.title.toLowerCase().includes(q) || (d.number ?? "").startsWith(q)
  const isOpen = (key: string) => Boolean(q) || open.has(key)

  const docLink = (d: KDoc, label = d.short) => {
    const active = d.slug === activeSlug
    return (
      <Link
        key={d.path}
        href={`/learn/${d.slug}`}
        ref={active ? activeRef : undefined}
        onClick={onNavigate}
        aria-current={active ? "page" : undefined}
        title={d.title}
        className={cn(
          "group/doc flex gap-2 rounded-md px-2 py-1.5 text-[13px] leading-snug transition-colors",
          active
            ? "bg-ui-main/10 font-medium text-ui-accent"
            : "text-muted-foreground hover:bg-muted hover:text-foreground",
        )}
      >
        {d.number ? (
          <span className="mt-px shrink-0 font-mono text-[10px] tabular-nums text-muted-foreground/70">
            {d.number}
          </span>
        ) : null}
        <span className="line-clamp-2">{label}</span>
      </Link>
    )
  }

  const groupBlock = (s: KSection, g: KGroup) => {
    const docs = g.docs.filter(matches)
    if (docs.length === 0) return null
    const key = `${s.key}::${g.key}`
    // A stage with one group needs no second fold.
    if (s.groups.length === 1)
      return (
        <div key={key} className="space-y-0.5">
          {docs.map((d) => docLink(d))}
        </div>
      )
    return (
      <div key={key}>
        <button
          type="button"
          onClick={() => toggle(key)}
          aria-expanded={isOpen(key)}
          className="flex w-full items-center gap-1.5 rounded-md px-2 py-1 text-left font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground hover:text-foreground"
        >
          <ChevronRight
            className={cn(
              "h-3 w-3 shrink-0 transition-transform",
              isOpen(key) && "rotate-90",
            )}
          />
          <span className="flex-1 truncate">
            {g.kind === "apply" && g.key !== "apply"
              ? `Apply · ${g.title}`
              : g.title}
          </span>
          <span className="tabular-nums">{docs.length}</span>
        </button>
        {isOpen(key) ? (
          <div className="ml-2 space-y-0.5 border-l border-border pl-2">
            {docs.map((d) => docLink(d))}
          </div>
        ) : null}
      </div>
    )
  }

  const startDocs = start.filter(matches)
  const visibleProjects = projects.filter(
    (p) => !q || p.title.toLowerCase().includes(q),
  )

  return (
    <nav aria-label="Knowledge hub" className="flex flex-col gap-3 p-4">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter topics…"
            aria-label="Filter topics"
            className="h-8 w-full rounded-md border border-input bg-background pl-8 pr-7 text-[13px] placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
          {query ? (
            <button
              type="button"
              onClick={() => setQuery("")}
              aria-label="Clear filter"
              className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded p-0.5 text-muted-foreground hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          ) : null}
        </div>
        <button
          type="button"
          onClick={() => setAll(true)}
          title="Expand all"
          aria-label="Expand all sections"
          className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <ChevronsUpDown className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => setAll(false)}
          title="Collapse all"
          aria-label="Collapse all sections"
          className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <ChevronsDownUp className="h-4 w-4" />
        </button>
      </div>

      <Link
        href="/"
        onClick={onNavigate}
        className={cn(
          "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium transition-colors",
          !activeSlug
            ? "bg-ui-main/10 text-ui-accent"
            : "text-foreground hover:bg-muted",
        )}
      >
        <Compass className="h-4 w-4" />
        Hub home
      </Link>

      {startDocs.length > 0 ? (
        <SectionFold
          label="Start here"
          icon={BookOpen}
          count={startDocs.length}
          open={isOpen("start")}
          onToggle={() => toggle("start")}
        >
          {startDocs.map((d) => docLink(d, d.title))}
        </SectionFold>
      ) : null}

      <div className="px-2 pt-1 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
        Learning path
      </div>

      <div className="space-y-1">
        {sections.map((s) => {
          const groups = s.groups.map((g) => groupBlock(s, g)).filter(Boolean)
          const overviewMatches =
            s.overview && (!q || s.title.toLowerCase().includes(q))
          if (q && groups.length === 0 && !overviewMatches) return null
          const total = s.groups.reduce((n, g) => n + g.docs.length, 0)
          return (
            <SectionFold
              key={s.key}
              label={s.title}
              number={s.number}
              icon={stageIcon(s.number)}
              count={total}
              open={isOpen(s.key)}
              onToggle={() => toggle(s.key)}
              highlighted={s.key === activeSection?.key}
            >
              {s.overview ? docLink(s.overview, "Stage overview") : null}
              {groups}
            </SectionFold>
          )
        })}
      </div>

      {visibleProjects.length > 0 ? (
        <SectionFold
          label="Projects"
          icon={Wrench}
          count={visibleProjects.length}
          open={isOpen("projects")}
          onToggle={() => toggle("projects")}
        >
          {visibleProjects.map((p) => (
            <Link
              key={p.title}
              href={p.href}
              onClick={onNavigate}
              className="flex items-center gap-2 rounded-md px-2 py-1.5 text-[13px] text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 shrink-0 rounded-full",
                  STATUS_DOT[p.status],
                )}
                aria-hidden
              />
              <span className="truncate">{p.title}</span>
              {p.status === "live" ? (
                <span className="ml-auto font-mono text-[9px] uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                  Live
                </span>
              ) : null}
            </Link>
          ))}
        </SectionFold>
      ) : null}
    </nav>
  )
}

function SectionFold({
  label,
  number,
  icon: Icon,
  count,
  open,
  onToggle,
  highlighted,
  children,
}: {
  label: string
  number?: number | null
  icon: LucideIcon
  count: number
  open: boolean
  onToggle: () => void
  highlighted?: boolean
  children: React.ReactNode
}) {
  return (
    <div>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className={cn(
          "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-muted",
          highlighted
            ? "font-semibold text-foreground"
            : "font-medium text-foreground/90",
        )}
      >
        <Icon
          className={cn(
            "h-4 w-4 shrink-0",
            highlighted ? "text-ui-accent" : "text-muted-foreground",
          )}
        />
        {number != null ? (
          <span className="w-4 shrink-0 font-mono text-[11px] tabular-nums text-muted-foreground">
            {number}
          </span>
        ) : null}
        <span className="flex-1 truncate">{label}</span>
        <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
          {count}
        </span>
        <ChevronRight
          className={cn(
            "h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform",
            open && "rotate-90",
          )}
        />
      </button>
      {open ? <div className="mt-0.5 space-y-0.5 pl-3">{children}</div> : null}
    </div>
  )
}
