import { ArrowRight, BookOpenText, Github, Hammer, Wrench } from "lucide-react"
import Link from "next/link"
import { KnowledgeShell } from "@/components/knowledge/knowledge-shell"
import { ProjectCards } from "@/components/knowledge/project-cards"
import { stageIcon } from "@/components/knowledge/stage-icons"
import { KNOWLEDGE_REPO_URL } from "@/lib/knowledge/source"
import { getKnowledgeTree, type KSection } from "@/lib/knowledge/tree"
import { SOLUTIONS, solutionStatus } from "@/lib/solutions"

/**
 * "/" — the AI engineering knowledge hub. Public.
 *
 * Content is read from github.com/sahupra1357/AISystems (see lib/knowledge),
 * so new lessons and stages appear here on the next hourly revalidation
 * without a deploy. The previous "AI operations desk" dashboard is preserved,
 * superuser-only, at /admin/dashboard-v1.
 */
// A literal, as Next's static analysis requires; matches KNOWLEDGE_REVALIDATE_SECONDS.
export const revalidate = 3600

/** Phases follow the repo's own suggested pacing (stages 1–3, 4–9, 10–12).
 *  A stage added past 12 lands in the last phase until it is placed. */
const PHASES: Array<{ label: string; caption: string; from: number; to: number }> = [
  { label: "Foundations", caption: "Python, math, classical ML, deep learning", from: 1, to: 3 },
  { label: "Building with LLMs", caption: "Prompts, context, RAG, agents, fine-tuning, evals", from: 4, to: 9 },
  { label: "Production", caption: "Serving, operating, architecture, capstones", from: 10, to: Number.MAX_SAFE_INTEGER },
]

export default async function KnowledgeHubPage() {
  const tree = await getKnowledgeTree()
  const lessons = tree.sections.reduce((n, s) => n + s.learnCount, 0)
  const scenarios = tree.sections.reduce((n, s) => n + s.applyCount, 0)
  const live = SOLUTIONS.filter((s) => solutionStatus(s) === "live").length
  const guide = tree.start[0]

  const stats = [
    { value: tree.sections.length, label: "stages" },
    { value: lessons, label: "lessons" },
    { value: scenarios, label: "field-manual scenarios" },
    { value: SOLUTIONS.length, label: `projects · ${live} live` },
  ]

  const unphased = tree.sections.filter((s) => s.number === null)

  return (
    <KnowledgeShell>
      {/* Hero */}
      <div className="dossier-dots bg-muted/20">
        <div className="px-6 py-14 sm:py-20 lg:px-10 2xl:px-14">
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-ui-accent">
            AI engineering knowledge hub
          </p>
          <h1 className="mt-4 max-w-3xl font-display text-4xl font-bold leading-[1.05] tracking-tight text-foreground sm:text-5xl">
            From first principles to production AI systems.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            One path in {tree.sections.length} stages: lessons that explain why things work, and a field manual
            of production scenarios — each with implementation steps, trade-offs, a checklist and metrics.
            Plus working projects that put it to use.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            {guide ? (
              <Link
                href={`/learn/${guide.slug}`}
                className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-5 text-sm font-semibold text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
              >
                Start the guide <ArrowRight className="h-4 w-4" />
              </Link>
            ) : null}
            <Link
              href="#learning-path"
              className="inline-flex h-10 items-center gap-2 rounded-md border border-border bg-background px-5 text-sm font-semibold text-foreground transition-colors hover:bg-muted"
            >
              Browse the stages
            </Link>
            <a
              href={KNOWLEDGE_REPO_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-10 items-center gap-2 px-2 text-sm font-medium text-muted-foreground hover:text-foreground"
            >
              <Github className="h-4 w-4" /> Source on GitHub
            </a>
          </div>

          <dl className="mt-12 grid max-w-4xl grid-cols-2 gap-x-6 gap-y-5 border-t border-border pt-6 sm:grid-cols-4">
            {stats.map((s) => (
              <div key={s.label}>
                <dt className="sr-only">{s.label}</dt>
                <dd className="font-display text-3xl font-bold tabular-nums text-foreground">{s.value}</dd>
                <dd className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                  {s.label}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </div>

      <div className="space-y-16 px-6 py-14 lg:px-10 2xl:px-14">
        {/* How it's organised */}
        <section aria-label="How the hub is organised" className="grid gap-4 sm:grid-cols-3">
          {[
            { icon: BookOpenText, title: "Learn", body: "Curriculum lessons, exercises and checklists — why things work." },
            { icon: Wrench, title: "Apply", body: "Field-manual scenarios to reach for when you are building." },
            { icon: Hammer, title: "Projects", body: "Working systems built on these notes — several run live here." },
          ].map(({ icon: Icon, title, body }) => (
            <div key={title} className="flex gap-3 rounded-lg border border-border p-4">
              <Icon className="mt-0.5 h-5 w-5 shrink-0 text-ui-accent" />
              <div>
                <p className="text-sm font-semibold text-foreground">{title}</p>
                <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">{body}</p>
              </div>
            </div>
          ))}
        </section>

        {/* Learning path */}
        <section id="learning-path" aria-labelledby="path-heading" className="scroll-mt-20">
          <div className="mb-6 border-b border-border pb-3">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-ui-accent">The path</p>
            <h2 id="path-heading" className="font-display text-2xl font-bold tracking-tight text-foreground">
              Learning path
            </h2>
          </div>

          <div className="space-y-10">
            {PHASES.map((phase) => {
              const stages = tree.sections.filter(
                (s) => s.number !== null && s.number >= phase.from && s.number <= phase.to,
              )
              if (stages.length === 0) return null
              return (
                <div key={phase.label}>
                  <div className="mb-3 flex flex-wrap items-baseline gap-x-3">
                    <h3 className="text-sm font-semibold text-foreground">{phase.label}</h3>
                    <p className="text-[13px] text-muted-foreground">{phase.caption}</p>
                  </div>
                  <StageGrid stages={stages} />
                </div>
              )
            })}
            {unphased.length > 0 ? <StageGrid stages={unphased} /> : null}
          </div>
        </section>

        <ProjectCards />
      </div>
    </KnowledgeShell>
  )
}

function StageGrid({ stages }: { stages: KSection[] }) {
  return (
    <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
      {stages.map((s) => {
        const Icon = stageIcon(s.number)
        const href = s.overview ? `/learn/${s.overview.slug}` : `/learn/${s.groups[0]?.docs[0]?.slug ?? ""}`
        return (
          <li key={s.key}>
            <Link
              href={href}
              className="group flex h-full flex-col gap-2 rounded-lg border border-border bg-card p-4 transition-all hover:-translate-y-0.5 hover:border-ui-main/40 hover:shadow-sm"
            >
              <div className="flex items-center gap-2.5">
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-ui-main/10 text-ui-accent transition-colors group-hover:bg-ui-main group-hover:text-white">
                  <Icon className="h-4 w-4" />
                </span>
                <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
                  {s.number != null ? `Stage ${s.number}` : "Extra"}
                </span>
              </div>
              <p className="text-[15px] font-semibold leading-snug text-foreground">{s.title}</p>
              {s.blurb ? <p className="flex-1 text-[13px] leading-relaxed text-muted-foreground">{s.blurb}</p> : <div className="flex-1" />}
              <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                {s.learnCount} lessons
                {s.applyCount ? ` · ${s.applyCount} scenarios` : ""}
              </p>
            </Link>
          </li>
        )
      })}
    </ol>
  )
}
