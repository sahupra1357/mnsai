import { ToolDemoDialog } from "@/components/dashboard/tool-demo-dialog"
import { Card, CardContent } from "@/components/ui/card"
import {
  ArrowRight,
  ClipboardCheck,
  FileSignature,
  FileText,
  Github,
  GraduationCap,
  ScanSearch,
  Table2,
} from "lucide-react"
import Link from "next/link"

/**
 * The tools desk — the "act on it" layer under AI Pulse. Mono-teal treatment
 * (no per-card pastel accents) so the cards read as one product family and
 * match /profile's visual language.
 */

/** Each tool has its own repo; `source` points at the repo root so GitHub
 *  renders that project's README. Every linked repo must stay public — this is
 *  a public page, and GitHub serves private repos as a bare 404, so a link to
 *  one reads as broken rather than restricted. A tool whose repo is still
 *  private omits `source` and shows no link at all, which is honest; add the
 *  link back once the repo is public. */
const GH = "https://github.com/sahupra1357"

/** A card links to an in-app route (`href`) or, for a tool that runs on your
 *  own machine and has nothing to open here, to a screen recording (`demo`).
 *  Exactly one of the two — that pair is the card's primary action. */
type Solution = {
  icon: typeof FileText
  title: string
  description: string
  source?: string
  href?: string
  demo?: { src: string; poster?: string }
}

const solutions: Solution[] = [
  {
    icon: FileText,
    title: "Data Extraction",
    description:
      "Extract structured data from PDFs, invoices, and scanned documents using AI.",
    href: "/document-extractions",
    source: `${GH}/mnsai`,
  },
  {
    icon: FileSignature,
    title: "Contract Review",
    description:
      "Review contracts with AI to surface risky clauses, obligations, and key terms.",
    href: "/solutions/contract-review",
    source: `${GH}/ContractReviewSystem`,
  },
  {
    icon: GraduationCap,
    title: "Career Explorer Empowered by AI",
    description:
      "Compare fields of study, then find the colleges that teach the course you want — every fact sourced.",
    href: "/solutions/course-search",
    source: `${GH}/ai-career-explorer`,
  },
  {
    icon: ClipboardCheck,
    title: "ATS Resume Matcher",
    description:
      "Match your resume against job descriptions and get an ATS compatibility score.",
    href: "/solutions/ats-resume-matcher",
    source: `${GH}/AIResumeMatcher`,
  },
  {
    icon: ScanSearch,
    title: "Semantic Document Search",
    description:
      "Search documents of any shape by meaning, with every hit highlighted in place in the original.",
    href: "/solutions/similarity-search",
    // sahupra1357/SimilaritySearch is private; no link until it is public.
  },
  {
    icon: Table2,
    title: "Coding Agent Viewer",
    description:
      "Browse what your Claude Code and Codex sessions actually did — transcripts and token spend from your local logs, in one filterable table.",
    demo: {
      src: "/assets/videos/coding-agent-viewer-demo.mp4",
      poster: "/assets/videos/coding-agent-viewer-demo-poster.jpg",
    },
    source: `${GH}/CodingAgentViewer`,
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

      {/* Three across: four or more columns leave orphans on the second row
          at these counts, and squeeze each card under ~210px. */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {solutions.map(
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
                  ) : null}

                  {source ? (
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
