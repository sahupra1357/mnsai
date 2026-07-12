import Link from "next/link"
import { ArrowUpRight } from "lucide-react"
import {
  projects,
  sections,
  projectCtaLabel,
  projectBuiltWithLabel,
} from "./profile-data"
import { SectionHeading } from "./section-heading"

/**
 * Live demos keep cards (design move 8) — they're products — but with a
 * consistent "Live demo →" affordance and a mono "Built with" note. Single
 * column in the reading measure so they don't read as a generic marketing grid.
 */
export function ProjectsShowcase() {
  const meta = sections.demos
  return (
    <section id={meta.id} className="scroll-mt-24">
      <SectionHeading meta={meta} />

      <div className="flex flex-col gap-4">
        {projects.map(({ icon: Icon, title, description, builtWith, href }) => (
          <Link
            key={title}
            href={href}
            className="group flex items-start gap-4 rounded-xl border border-border bg-card p-5 transition-colors hover:border-ui-accent/40 hover:bg-ui-accent/[0.03] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ui-accent sm:p-6"
          >
            <span className="mt-0.5 inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-ui-accent/10 text-ui-accent transition-colors group-hover:bg-ui-main group-hover:text-white">
              <Icon className="h-5 w-5" />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-display text-lg font-semibold tracking-tight text-foreground">
                  {title}
                </h3>
                <span className="inline-flex shrink-0 items-center gap-1 text-sm font-semibold text-ui-accent">
                  {projectCtaLabel}
                  <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </span>
              </div>
              <p className="mt-1.5 text-[15px] leading-relaxed text-muted-foreground">
                {description}
              </p>
              <p className="mt-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground/80">
                {projectBuiltWithLabel}: {builtWith}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </section>
  )
}
