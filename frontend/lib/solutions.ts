import {
  Bot,
  Braces,
  Briefcase,
  ClipboardCheck,
  FileSignature,
  FileText,
  GraduationCap,
  type LucideIcon,
  ScanSearch,
  Table2,
} from "lucide-react"

/**
 * The single catalogue of mnsAI tools. The nav's "Solutions" dropdown and the
 * dashboard's "Your tools" grid both render this list, so an entry added here
 * shows up in both and the two can never drift apart again.
 *
 * `source` points at the repo root so GitHub renders that project's README.
 * Every linked repo must stay public — these are public surfaces, and GitHub
 * serves a private repo as a bare 404, so a link to one reads as broken rather
 * than restricted. A tool whose repo is still private omits `source`.
 */
const GH = "https://github.com/sahupra1357"

export type Solution = {
  icon: LucideIcon
  title: string
  /** One line for the nav dropdown — shorter than `description`. */
  navSubLabel: string
  /** The card's body copy. */
  description: string
  /** In-app route, when the tool runs here. */
  href?: string
  /** Screen recording, for a tool that runs on your own machine instead. */
  demo?: { src: string; poster?: string }
  /** Public repo. */
  source?: string
}

/** The dashboard section the nav falls back to for a tool with no route. */
export const TOOLS_ANCHOR = "tools"

export const SOLUTIONS: Solution[] = [
  {
    icon: FileText,
    title: "Data Extraction",
    navSubLabel: "Review OCR results with confidence and parser provenance",
    description:
      "Extract structured data from PDFs, invoices, and scanned documents using AI.",
    href: "/document-extractions",
    source: `${GH}/mnsai`,
  },
  {
    icon: Braces,
    title: "Contract Field Extraction",
    navSubLabel:
      "Pull 10 key contract fields to JSON, verify blanks, and store the row",
    description:
      "Pull ten key contract fields into a strict JSON record, verify every blank by hand against the document, and keep the row.",
    href: "/contract-extraction",
    source: `${GH}/mnsai`,
  },
  {
    icon: FileSignature,
    title: "Contract Review",
    navSubLabel: "AI review of contracts for risks, clauses, and obligations",
    description:
      "Review contracts with AI to surface risky clauses, obligations, and key terms.",
    href: "/solutions/contract-review",
    source: `${GH}/ContractReviewSystem`,
  },
  {
    icon: GraduationCap,
    title: "Career Explorer Empowered by AI",
    navSubLabel:
      "Evidence-backed research on any field and the colleges that teach it",
    description:
      "Compare fields of study, then find the colleges that teach the course you want — every fact sourced.",
    href: "/solutions/course-search",
    source: `${GH}/ai-career-explorer`,
  },
  {
    icon: ClipboardCheck,
    title: "ATS Resume Matcher",
    navSubLabel: "Match your resume to any job description",
    description:
      "Match your resume against job descriptions and get an ATS compatibility score.",
    href: "/solutions/ats-resume-matcher",
    source: `${GH}/AIResumeMatcher`,
  },
  {
    icon: Briefcase,
    title: "HireFlow Automation",
    navSubLabel:
      "Find roles, tailor your resume per posting, and fill applications",
    description:
      "Claude Code as a job-search-and-apply agent: finds roles, captures job descriptions, tailors your resume per posting, and fills application forms — stopping before submit.",
    demo: {
      src: "/assets/videos/hireflow-demo.mp4",
      poster: "/assets/videos/hireflow-demo-poster.jpg",
    },
    source: `${GH}/HireFlowAutomation`,
  },
  {
    icon: ScanSearch,
    title: "Semantic Document Search",
    navSubLabel:
      "Search mixed documents by meaning and see each hit in its source",
    description:
      "Search documents of any shape by meaning, with every hit highlighted in place in the original.",
    href: "/solutions/similarity-search",
    // sahupra1357/SimilaritySearch is private; no link until it is public.
  },
  {
    icon: Table2,
    title: "Coding Agent Viewer",
    navSubLabel:
      "Browse your local Claude Code and Codex sessions and their token spend",
    description:
      "Browse what your Claude Code and Codex sessions actually did — transcripts and token spend from your local logs, in one filterable table.",
    demo: {
      src: "/assets/videos/coding-agent-viewer-demo.mp4",
      poster: "/assets/videos/coding-agent-viewer-demo-poster.jpg",
    },
    source: `${GH}/CodingAgentViewer`,
  },
  {
    icon: Bot,
    title: "mnsAI Agent OS",
    navSubLabel:
      "Durable, provider-neutral agent harness for local and cloud models",
    description:
      "A durable agent runtime: run the same agent on Ollama, llama.cpp, or Modal by switching one config profile, with persisted runs, resume after a crash, and hard step, token and cost budgets.",
    source: `${GH}/mnsAIAgentOS`,
  },
]

/** How far a visitor can go with a tool from this site, strongest first:
 *  - "live"   — it runs here; open it and use it.
 *  - "demo"   — it runs on your own machine; a screen recording shows it working.
 *  - "source" — code only, for now. */
export type SolutionStatus = "live" | "demo" | "source"

export function solutionStatus(solution: Solution): SolutionStatus {
  if (solution.href) return "live"
  if (solution.demo) return "demo"
  return "source"
}

/**
 * Where the nav sends you for a tool. A tool with no in-app route (it runs on
 * your own machine) lands on the tools desk, where its card carries the demo
 * or the repo link — the dropdown never throws you off-site unannounced.
 */
export function solutionNavHref(solution: Solution): string {
  return solution.href ?? `/#${TOOLS_ANCHOR}`
}
