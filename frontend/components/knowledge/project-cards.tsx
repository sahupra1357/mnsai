import { ArrowRight, Github } from "lucide-react"
import Link from "next/link"
import { ToolDemoDialog } from "@/components/dashboard/tool-demo-dialog"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import {
  SOLUTIONS,
  type SolutionStatus,
  solutionStatus,
  TOOLS_ANCHOR,
} from "@/lib/solutions"

const BADGE: Record<
  SolutionStatus,
  { label: string; className: string; dot: string }
> = {
  live: {
    label: "Live demo",
    className:
      "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
    dot: "bg-emerald-500",
  },
  demo: {
    label: "Demo video",
    className:
      "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
    dot: "bg-amber-500",
  },
  source: {
    label: "Source",
    className: "border-border bg-muted text-muted-foreground",
    dot: "bg-muted-foreground/50",
  },
}

/**
 * Projects built on the knowledge in the hub. Catalogue order is kept (it is
 * shared with the nav's Solutions menu); what a visitor can actually do with
 * each one is carried by the badge and the card's weight instead — a tool
 * that runs here gets the teal ring and a pulsing "Live demo" lamp.
 *
 * Same two-destination pattern as the old tools grid: the primary action
 * stretches over the card via ::after, the source link sits above on z-10.
 */
export function ProjectCards() {
  const counts = SOLUTIONS.reduce(
    (acc, s) => ({ ...acc, [solutionStatus(s)]: acc[solutionStatus(s)] + 1 }),
    { live: 0, demo: 0, source: 0 } as Record<SolutionStatus, number>,
  )

  return (
    <section
      id={TOOLS_ANCHOR}
      aria-labelledby="projects-heading"
      className="scroll-mt-20"
    >
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-border pb-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-ui-accent">
            Built with it
          </p>
          <h2
            id="projects-heading"
            className="font-display text-2xl font-bold tracking-tight text-foreground"
          >
            Projects
          </h2>
        </div>
        <ul className="flex flex-wrap gap-3 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          {(Object.keys(BADGE) as SolutionStatus[]).map((k) =>
            counts[k] ? (
              <li key={k} className="flex items-center gap-1.5">
                <span
                  className={cn("h-1.5 w-1.5 rounded-full", BADGE[k].dot)}
                  aria-hidden
                />
                {counts[k]} {BADGE[k].label}
              </li>
            ) : null,
          )}
        </ul>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
        {SOLUTIONS.map((solution, i) => {
          const {
            icon: Icon,
            title,
            description,
            href,
            demo,
            source,
          } = solution
          const status = solutionStatus(solution)
          const badge = BADGE[status]
          return (
            <Card
              key={title}
              className={cn(
                "group relative flex h-full flex-col border transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md focus-within:border-ui-main/50",
                status === "live"
                  ? "border-ui-main/35 bg-gradient-to-b from-ui-main/[0.06] to-transparent ring-1 ring-ui-main/10 hover:border-ui-main/60"
                  : "border-border hover:border-ui-main/40",
              )}
            >
              <CardContent className="flex h-full flex-col gap-3 p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-ui-main/10 text-ui-accent transition-colors duration-200 group-hover:bg-ui-main group-hover:text-white">
                    <Icon className="h-[18px] w-[18px]" />
                  </div>
                  <span
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider",
                      badge.className,
                    )}
                  >
                    <span className="relative flex h-1.5 w-1.5" aria-hidden>
                      {status === "live" ? (
                        <span
                          className={cn(
                            "absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 motion-reduce:hidden",
                            badge.dot,
                          )}
                        />
                      ) : null}
                      <span
                        className={cn(
                          "relative inline-flex h-1.5 w-1.5 rounded-full",
                          badge.dot,
                        )}
                      />
                    </span>
                    {badge.label}
                  </span>
                </div>
                <h3 className="text-[15px] font-semibold leading-snug text-foreground">
                  <span className="mr-1.5 font-mono text-[11px] font-normal text-muted-foreground">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  {title}
                </h3>
                <p className="flex-1 text-[13px] leading-relaxed text-muted-foreground">
                  {description}
                </p>

                <div className="flex items-center justify-between gap-2 pt-1">
                  {href ? (
                    <Link
                      href={href}
                      className="inline-flex items-center text-xs font-semibold text-ui-accent after:absolute after:inset-0 after:content-[''] hover:underline"
                    >
                      Try it live <ArrowRight className="ml-1 h-3 w-3" />
                    </Link>
                  ) : demo ? (
                    <ToolDemoDialog
                      title={title}
                      description={description}
                      src={demo.src}
                      poster={demo.poster}
                    />
                  ) : source ? (
                    <a
                      href={source}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs font-semibold text-ui-accent after:absolute after:inset-0 after:content-[''] hover:underline"
                    >
                      <Github className="h-3.5 w-3.5" />
                      View on GitHub
                    </a>
                  ) : null}

                  {source && (href || demo) ? (
                    <a
                      href={source}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`${title} source code on GitHub`}
                      title="View source on GitHub"
                      className="relative z-10 inline-flex items-center gap-1 rounded px-1.5 py-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
                    >
                      <Github className="h-3.5 w-3.5" />
                      Source
                    </a>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </section>
  )
}
