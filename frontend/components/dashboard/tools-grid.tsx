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
      <div className="mb-4 flex items-center gap-2 border-b border-border pb-2">
        <span className="h-2 w-2 rounded-[1px] bg-ui-main" aria-hidden="true" />
        <h2 className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-foreground">
          Your Tools
        </h2>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        {solutions.map(({ icon: Icon, title, description, href }) => (
          <Link key={title} href={href} className="group">
            <Card className="h-full border border-border transition-all duration-200 hover:border-ui-main/40 hover:shadow-md">
              <CardContent className="flex h-full flex-col gap-3 pb-6 pt-6">
                <div className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-ui-main/10 text-ui-accent transition-colors duration-200 group-hover:bg-ui-main group-hover:text-white">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="font-semibold text-foreground">{title}</h3>
                <p className="flex-1 text-sm leading-relaxed text-muted-foreground">
                  {description}
                </p>
                <span className="mt-1 inline-flex items-center text-xs font-semibold text-ui-accent group-hover:underline">
                  Open <ArrowRight className="ml-1 h-3 w-3" />
                </span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <p className="mt-5 border border-dashed border-border bg-muted/20 px-4 py-3 text-center font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
        More tools in progress
      </p>
    </section>
  )
}
