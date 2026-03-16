"use client"

import FileUploaderTS from "@/components/file-upload/file-uploader-ts"
import { Card, CardContent } from "@/components/ui/card"
import {
  BrainCircuit,
  FileText,
  Zap,
  LayoutDashboard,
  ShieldCheck,
  Download,
  Upload,
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

export default function ExtractorPage() {
  return (
    <div className="min-h-screen bg-background">

      {/* ── Hero ── */}
      <section className="relative flex flex-col items-center justify-center text-center px-6 py-20 overflow-hidden">
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
        <h1 className="text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl lg:text-6xl max-w-3xl leading-tight">
          Extract Data from{" "}
          <span className="text-ui-main">Any Document</span>{" "}
          in Seconds
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-muted-foreground leading-relaxed">
          mnsAI uses advanced AI to turn messy PDFs, invoices, receipts, and
          scanned forms into clean, structured data — instantly, accurately, and
          at scale.
        </p>
      </section>

      {/* ── Uploader ── */}
      <section className="px-6 pb-16">
        <div className="mx-auto max-w-3xl">
          <Card>
            <CardContent className="pt-6 pb-6">
              <FileUploaderTS />
            </CardContent>
          </Card>
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="px-6 py-16 bg-muted/30">
        <div className="mx-auto max-w-5xl">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-bold text-foreground sm:text-3xl">
              How it works
            </h2>
            <p className="mt-3 text-muted-foreground">
              Three simple steps from document to data.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
            {steps.map(({ number, icon: Icon, title, description }, i) => (
              <div key={number} className="flex flex-col items-center text-center gap-4 relative">
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

      {/* ── Features ── */}
      <section className="px-6 py-16">
        <div className="mx-auto max-w-6xl">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-bold text-foreground sm:text-3xl">
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

    </div>
  )
}
