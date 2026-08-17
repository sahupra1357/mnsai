import { Card, CardContent } from "@/components/ui/card"
import {
  ArrowRight,
  ClipboardCheck,
  FileSignature,
  FileText,
  GraduationCap,
} from "lucide-react"
import Link from "next/link"

/**
 * The tools desk — the "act on it" layer under AI Pulse. Mono-teal treatment
 * (no per-card pastel accents) so the cards read as one product family and
 * match /profile's visual language.
 */
const solutions = [
  {
    icon: FileText,
    title: "Data Extraction",
    description:
      "Extract structured data from PDFs, invoices, and scanned documents using AI.",
    href: "/document-extractions",
  },
  {
    icon: FileSignature,
    title: "Contract Review",
    description:
      "Review contracts with AI to surface risky clauses, obligations, and key terms.",
    href: "/solutions/contract-review",
  },
  {
    icon: GraduationCap,
    title: "Career Explorer Empowered by AI",
    description:
      "Compare fields of study, then find the colleges that teach the course you want — every fact sourced.",
    href: "/solutions/course-search",
  },
  {
    icon: ClipboardCheck,
    title: "ATS Resume Matcher",
    description:
      "Match your resume against job descriptions and get an ATS compatibility score.",
    href: "/solutions/ats-resume-matcher",
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
        {solutions.map(({ icon: Icon, title, description, href }) => (
          <Link key={title} href={href} className="group">
            <Card className="h-full border border-border transition-all duration-200 hover:-translate-y-0.5 hover:border-ui-main/40 hover:shadow-md">
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
                <span className="inline-flex items-center text-xs font-semibold text-ui-accent group-hover:underline">
                  Open <ArrowRight className="ml-1 h-3 w-3" />
                </span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </section>
  )
}
