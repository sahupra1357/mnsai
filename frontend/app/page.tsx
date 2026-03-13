import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import WithSubnavigation from "@/components/common/with-subnavigation"
import {
  FileText,
  Zap,
  LayoutDashboard,
  Upload,
  BrainCircuit,
  Download,
  ShieldCheck,
  ArrowRight,
} from "lucide-react"

const features = [
  {
    icon: BrainCircuit,
    title: "AI-Powered Extraction",
    description:
      "Leverage large language models to extract structured data from any document — invoices, receipts, contracts, and more.",
  },
  {
    icon: FileText,
    title: "Any Document Format",
    description:
      "Upload PDFs, images, and scanned documents. mnsAI handles noisy scans and complex layouts with ease.",
  },
  {
    icon: Zap,
    title: "Instant Structured Output",
    description:
      "Get clean JSON or Markdown output in seconds, ready to plug into your workflow or downstream systems.",
  },
  {
    icon: LayoutDashboard,
    title: "Unified Dashboard",
    description:
      "Manage all your extraction jobs, users, and settings from a single, intuitive control panel.",
  },
  {
    icon: ShieldCheck,
    title: "Secure & Private",
    description:
      "Your documents stay private. Role-based access control ensures only the right people see the right data.",
  },
  {
    icon: Download,
    title: "Export & Integrate",
    description:
      "Download results or connect via REST API to integrate mnsAI directly into your existing tools and pipelines.",
  },
]

const steps = [
  {
    number: "01",
    icon: Upload,
    title: "Upload Your Document",
    description:
      "Drag and drop or browse to upload a PDF, image, or scanned file from anywhere.",
  },
  {
    number: "02",
    icon: BrainCircuit,
    title: "AI Analyses the Content",
    description:
      "Our extraction engine reads the document, identifies its type, and pulls out every relevant field.",
  },
  {
    number: "03",
    icon: Download,
    title: "Download Structured Data",
    description:
      "Receive clean JSON or Markdown output instantly — copy it, export it, or send it to your API.",
  },
]

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <WithSubnavigation />

      {/* ── Hero ── */}
      <section className="relative flex flex-col items-center justify-center text-center px-6 py-28 overflow-hidden">
        {/* subtle radial glow */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 -z-10"
          style={{
            background:
              "radial-gradient(ellipse 80% 60% at 50% -10%, rgba(0,74,173,0.12) 0%, transparent 70%)",
          }}
        />

        <span className="inline-flex items-center gap-2 rounded-full border border-ui-main/20 bg-ui-main/5 px-4 py-1.5 text-xs font-semibold text-ui-main uppercase tracking-widest mb-6">
          AI Document Intelligence
        </span>

        <h1 className="text-5xl font-extrabold tracking-tight text-foreground sm:text-6xl lg:text-7xl max-w-4xl leading-tight">
          Extract Data from{" "}
          <span className="text-ui-main">Any Document</span>{" "}
          in Seconds
        </h1>

        <p className="mt-6 max-w-2xl text-lg text-muted-foreground leading-relaxed">
          mnsAI uses advanced AI to turn messy PDFs, invoices, receipts, and
          scanned forms into clean, structured data — instantly, accurately, and
          at scale.
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

      {/* ── Features ── */}
      <section className="px-6 py-20 bg-muted/30">
        <div className="mx-auto max-w-6xl">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-foreground sm:text-4xl">
              Everything you need to unlock your documents
            </h2>
            <p className="mt-3 text-muted-foreground max-w-xl mx-auto">
              From upload to structured output, mnsAI handles the full extraction
              pipeline so you don&apos;t have to.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map(({ icon: Icon, title, description }) => (
              <Card
                key={title}
                className="group hover:shadow-md transition-shadow duration-200 border border-border"
              >
                <CardContent className="pt-6 pb-6 flex flex-col gap-3">
                  <div className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-ui-main/10 text-ui-main group-hover:bg-ui-main group-hover:text-white transition-colors duration-200">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="font-semibold text-foreground">{title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-5xl">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-foreground sm:text-4xl">
              How it works
            </h2>
            <p className="mt-3 text-muted-foreground">
              Three simple steps from document to data.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
            {steps.map(({ number, icon: Icon, title, description }, i) => (
              <div key={number} className="flex flex-col items-center text-center gap-4 relative">
                {/* connector line */}
                {i < steps.length - 1 && (
                  <div
                    aria-hidden
                    className="hidden sm:block absolute top-7 left-[calc(50%+2.5rem)] w-[calc(100%-5rem)] h-px bg-border"
                  />
                )}
                <div className="relative z-10 flex items-center justify-center w-14 h-14 rounded-2xl bg-ui-main text-white shadow-lg">
                  <Icon className="h-6 w-6" />
                </div>
                <span className="text-xs font-bold text-ui-main tracking-widest">{number}</span>
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
            Start extracting smarter today
          </h2>
          <p className="mt-4 text-blue-100 text-lg">
            Join teams who rely on mnsAI to turn documents into actionable data — faster than ever before.
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
