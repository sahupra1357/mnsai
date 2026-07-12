import Link from "next/link"
import { ArrowUpRight } from "lucide-react"
import { platformProject, projects } from "@/lib/profile-data"
import { FeaturedPanel } from "./featured-panel"
import { ChatOpenLink } from "./chat-prefill-link"

/**
 * Projects. A wide intro panel describes this site itself (profile + RAG chat
 * agent) as a working project and links to the assistant. Below it, the three
 * live demos render as a 2-col card grid. No extra placeholder cards here — the
 * grid is intentionally these items only.
 */
export function ProjectsGrid() {
  return (
    <div className="space-y-8">
      {/* This-site intro panel */}
      <FeaturedPanel
        icon={platformProject.icon}
        badge={platformProject.badge}
        title={platformProject.title}
        description={platformProject.description}
        bullets={platformProject.bullets}
        chips={platformProject.chips}
        ctaSlot={<ChatOpenLink>{platformProject.ctaLabel}</ChatOpenLink>}
      />

      {/* Live-demo cards */}
      <div className="grid gap-5 sm:grid-cols-2">
        {projects.map((p) => {
          const Icon = p.icon
          return (
            <Link
              key={p.title}
              href={p.href}
              className="group flex flex-col rounded-2xl border border-border bg-card p-6 shadow-sm transition-all hover:border-ui-accent/40 hover:shadow-md"
            >
              <div className="flex items-center justify-between">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-ui-accent/10 text-ui-accent">
                  <Icon className="h-5 w-5" />
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  {p.status}
                </span>
              </div>

              <h3 className="mt-5 font-display text-xl font-bold tracking-tight text-foreground">
                {p.title}
              </h3>
              <p className="mt-2 flex-1 text-sm leading-relaxed text-muted-foreground">
                {p.description}
              </p>

              <ul className="mt-5 flex flex-wrap gap-2">
                {p.chips.map((c) => (
                  <li
                    key={c}
                    className="rounded-md border border-border bg-background px-2.5 py-1 font-mono text-xs text-muted-foreground"
                  >
                    {c}
                  </li>
                ))}
              </ul>

              <span className="mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-ui-accent">
                {p.ctaLabel}
                <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </span>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
