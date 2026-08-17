import { Card, CardContent } from "@/components/ui/card"
import {
  ArrowRight,
  ClipboardCheck,
  FileSignature,
  FileText,
  Github,
  GraduationCap,
} from "lucide-react"
import Link from "next/link"

/**
 * The tools desk — the "act on it" layer under AI Pulse. Mono-teal treatment
 * (no per-card pastel accents) so the cards read as one product family and
 * match /profile's visual language.
 */

/** Every tool lives in this repo, so `source` is a path within it rather than
 *  a separate repo URL. Parens are percent-encoded because the App Router
 *  route group `(protected)` is part of each path. */
const REPO = "https://github.com/sahupra1357/mnsai/tree/main"
const APP = "frontend/app/%28protected%29"

const solutions = [
  {
    icon: FileText,
    title: "Data Extraction",
    description:
      "Extract structured data from PDFs, invoices, and scanned documents using AI.",
    href: "/document-extractions",
    source: `${REPO}/${APP}/document-extractions`,
  },
  {
    icon: FileSignature,
    title: "Contract Review",
    description:
      "Review contracts with AI to surface risky clauses, obligations, and key terms.",
    href: "/solutions/contract-review",
    source: `${REPO}/${APP}/solutions/contract-review`,
  },
  {
    icon: GraduationCap,
    title: "Career Explorer Empowered by AI",
    description:
      "Compare fields of study, then find the colleges that teach the course you want — every fact sourced.",
    href: "/solutions/course-search",
    source: `${REPO}/${APP}/solutions/course-search`,
  },
  {
    icon: ClipboardCheck,
    title: "ATS Resume Matcher",
    description:
      "Match your resume against job descriptions and get an ATS compatibility score.",
    href: "/solutions/ats-resume-matcher",
    source: `${REPO}/${APP}/solutions/ats-resume-matcher`,
  },
]

export function ToolsGrid() {
  return (
    <section aria-label="mnsAI tools">
      <div className="mb-6 flex items-baseline justify-between gap-4 border-b border-border pb-3">
        <h2 className="font-display text-2xl font-bold tracking-tight text-foreground">
          Your tools
        </h2>
        <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          {solutions.length} available
        </p>
      </div>

      {/* Four across on wide screens: the set reads as one row of instruments
          rather than a 2x2 block with a short column beside it. */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {solutions.map(({ icon: Icon, title, description, href, source }) => (
          // Two destinations per card, so the card itself can't be an anchor:
          // "Open" stretches over the whole card via ::after, and the source
          // link sits above it on z-10. Nesting <a> inside <a> would be
          // invalid and would swallow the inner link's clicks.
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
                <Link
                  href={href}
                  className="inline-flex items-center text-xs font-semibold text-ui-accent after:absolute after:inset-0 after:content-[''] hover:underline"
                >
                  Open <ArrowRight className="ml-1 h-3 w-3" />
                </Link>

                <a
                  href={source}
                  target="_blank"
                  rel="noopener noreferrer"
                  // aria-label because the icon alone gives no accessible name,
                  // and four identical "Source" links need distinguishing.
                  aria-label={`${title} source code on GitHub`}
                  title="View source on GitHub"
                  className="relative z-10 inline-flex items-center gap-1 rounded px-1.5 py-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
                >
                  <Github className="h-3.5 w-3.5" />
                  Source
                </a>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  )
}
