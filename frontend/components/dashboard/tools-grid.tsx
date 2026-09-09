import { ToolDemoDialog } from "@/components/dashboard/tool-demo-dialog"
import { Card, CardContent } from "@/components/ui/card"
import { SOLUTIONS, TOOLS_ANCHOR } from "@/lib/solutions"
import { ArrowRight, Github } from "lucide-react"
import Link from "next/link"

/**
 * The tools desk — the "act on it" layer under AI Pulse. Mono-teal treatment
 * (no per-card pastel accents) so the cards read as one product family and
 * match /profile's visual language.
 *
 * The list itself lives in `lib/solutions.ts`, shared with the nav's
 * "Solutions" dropdown so the two stay in step.
 */
export function ToolsGrid() {
  return (
    <section
      // The nav links here for a tool that has no route of its own.
      id={TOOLS_ANCHOR}
      aria-label="mnsAI tools"
      className="scroll-mt-20"
    >
      <div className="mb-6 flex items-baseline justify-between gap-4 border-b border-border pb-3">
        <h2 className="font-display text-2xl font-bold tracking-tight text-foreground">
          Your tools
        </h2>
        <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          {SOLUTIONS.length} available
        </p>
      </div>

      {/* Three across: four or more columns leave orphans on the second row
          at these counts, and squeeze each card under ~210px. */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {SOLUTIONS.map(
          ({ icon: Icon, title, description, href, demo, source }) => (
            // Two destinations per card, so the card itself can't be an anchor:
            // the primary action stretches over the whole card via ::after, and
            // the source link sits above it on z-10. Nesting <a> inside <a>
            // would be invalid and would swallow the inner link's clicks.
            <Card
              key={title}
              className="group relative flex h-full flex-col border border-border transition-all duration-200 focus-within:border-ui-main/40 hover:-translate-y-0.5 hover:border-ui-main/40 hover:shadow-md"
            >
              <CardContent className="flex h-full flex-col gap-3 p-5">
                <div className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-ui-main/10 text-ui-accent transition-colors duration-200 group-hover:bg-ui-main group-hover:text-white">
                  <Icon className="h-[18px] w-[18px]" />
                </div>
                <h3 className="text-[15px] font-semibold leading-snug text-foreground">
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
                      Open <ArrowRight className="ml-1 h-3 w-3" />
                    </Link>
                  ) : demo ? (
                    <ToolDemoDialog
                      title={title}
                      description={description}
                      src={demo.src}
                      poster={demo.poster}
                    />
                  ) : source ? (
                    // Nothing to open here and no recording: the repo is the
                    // card's only destination, so it becomes the primary
                    // action rather than sitting in the corner as a footnote.
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

                  {/* Already the primary action above when there is no other
                      destination — don't repeat it. */}
                  {source && (href || demo) ? (
                    <a
                      href={source}
                      target="_blank"
                      rel="noopener noreferrer"
                      // aria-label because the icon alone gives no accessible
                      // name, and the repeated "Source" links need
                      // distinguishing from one another.
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
          ),
        )}
      </div>
    </section>
  )
}
