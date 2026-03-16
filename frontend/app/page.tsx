import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import WithSubnavigation from "@/components/common/with-subnavigation"
import {
  FileText,
  GraduationCap,
  ClipboardCheck,
  ArrowRight,
  BrainCircuit,
  ShieldCheck,
  Plug,
} from "lucide-react"

const solutions = [
  {
    icon: FileText,
    title: "Data Extraction",
    description:
      "Turn messy PDFs, invoices, receipts, and scanned forms into clean structured data — instantly and at scale.",
    href: "/extractor",
    available: true,
  },
  {
    icon: GraduationCap,
    title: "Course Search",
    description:
      "Find the best courses near you. Filter by category, mode, level, price, and college rating.",
    href: "/solutions/course-search",
    available: true,
  },
  {
    icon: ClipboardCheck,
    title: "ATS Resume Matcher",
    description:
      "Match your resume to any job description and get an ATS compatibility score with actionable feedback.",
    href: "/solutions/ats-resume-matcher",
    available: true,
  },
]

const pillars = [
  {
    icon: BrainCircuit,
    title: "AI at the Core",
    description:
      "Every solution is powered by large language models, delivering accuracy and intelligence that rule-based systems can't match.",
  },
  {
    icon: ShieldCheck,
    title: "Secure & Private",
    description:
      "Role-based access control and HttpOnly cookie auth keep your data visible only to the right people.",
  },
  {
    icon: Plug,
    title: "Easy to Integrate",
    description:
      "REST APIs and clean structured outputs make it simple to plug mnsAI into your existing tools and pipelines.",
  },
]

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <WithSubnavigation />

      {/* ── Hero ── */}
      <section className="relative flex flex-col items-center justify-center text-center px-6 py-28 overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 -z-10"
          style={{
            background:
              "radial-gradient(ellipse 80% 60% at 50% -10%, rgba(0,74,173,0.12) 0%, transparent 70%)",
          }}
        />

        <span className="inline-flex items-center gap-2 rounded-full border border-ui-main/20 bg-ui-main/5 px-4 py-1.5 text-xs font-semibold text-ui-main uppercase tracking-widest mb-6">
          AI-Powered Platform
        </span>

        <h1 className="text-5xl font-extrabold tracking-tight text-foreground sm:text-6xl lg:text-7xl max-w-4xl leading-tight">
          Smarter Tools for{" "}
          <span className="text-ui-main">Every Challenge</span>
        </h1>

        <p className="mt-6 max-w-2xl text-lg text-muted-foreground leading-relaxed">
          mnsAI brings together a growing suite of AI solutions — from document
          intelligence to career tools — all in one platform, ready to use in
          seconds.
        </p>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Button
            asChild
            size="lg"
            className="bg-ui-main hover:bg-[#003d8f] text-white font-semibold px-8 h-12 rounded-lg shadow-md"
          >
            <Link href="/signup">
              Get Started Free <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline" className="h-12 px-8 rounded-lg font-semibold">
            <Link href="/login">Sign In</Link>
          </Button>
        </div>

        <p className="mt-4 text-xs text-muted-foreground">
          No credit card required &middot; Free to try
        </p>
      </section>

      {/* ── Solutions ── */}
      <section className="px-6 py-20 bg-muted/30">
        <div className="mx-auto max-w-6xl">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-foreground sm:text-4xl">
              Our Solutions
            </h2>
            <p className="mt-3 text-muted-foreground max-w-xl mx-auto">
              A growing suite of AI tools built to save you time and effort
              across different domains.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {solutions.map(({ icon: Icon, title, description, href }) => (
              <Link key={title} href={href} className="group">
                <Card className="h-full hover:shadow-md transition-shadow duration-200 border border-border">
                  <CardContent className="pt-6 pb-6 flex flex-col gap-3 h-full">
                    <div className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-ui-main/10 text-ui-main group-hover:bg-ui-main group-hover:text-white transition-colors duration-200">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h3 className="font-semibold text-foreground">{title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed flex-1">
                      {description}
                    </p>
                    <span className="inline-flex items-center text-xs font-semibold text-ui-main group-hover:underline mt-2">
                      Open <ArrowRight className="ml-1 h-3 w-3" />
                    </span>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── Platform Pillars ── */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-5xl">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-foreground sm:text-4xl">
              Built on solid foundations
            </h2>
            <p className="mt-3 text-muted-foreground">
              Every tool on the platform shares the same core principles.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
            {pillars.map(({ icon: Icon, title, description }) => (
              <div key={title} className="flex flex-col items-center text-center gap-3">
                <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-ui-main text-white shadow-lg">
                  <Icon className="h-6 w-6" />
                </div>
                <h3 className="font-semibold text-foreground">{title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Bottom CTA ── */}
      <section className="px-6 py-20 bg-ui-main text-white text-center">
        <div className="mx-auto max-w-2xl">
          <h2 className="text-3xl font-bold sm:text-4xl">
            Start working smarter today
          </h2>
          <p className="mt-4 text-blue-100 text-lg">
            Sign up for free and explore the full suite of mnsAI solutions —
            no setup required.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Button
              asChild
              size="lg"
              className="bg-white text-ui-main hover:bg-blue-50 font-semibold px-8 h-12 rounded-lg"
            >
              <Link href="/signup">
                Create Free Account <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="border-white text-white hover:bg-white/10 h-12 px-8 rounded-lg font-semibold bg-transparent"
            >
              <Link href="/login">Sign In</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="px-6 py-8 border-t text-center text-sm text-muted-foreground">
        &copy; {new Date().getFullYear()} mnsAI. All rights reserved.
      </footer>
    </div>
  )
}
