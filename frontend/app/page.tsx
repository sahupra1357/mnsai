"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import useAuth from "@/hooks/use-auth"
import WithSubnavigation from "@/components/common/with-subnavigation"
import { Card, CardContent } from "@/components/ui/card"
import {
  FileText,
  FileSignature,
  GraduationCap,
  ClipboardCheck,
  ArrowRight,
} from "lucide-react"

const solutions = [
  {
    icon: FileText,
    title: "Data Extraction",
    description: "Extract structured data from PDFs, invoices, and scanned documents using AI.",
    href: "/document-extractions",
    color: "bg-blue-500/10 text-blue-600 group-hover:bg-blue-500 group-hover:text-white",
  },
  {
    icon: FileSignature,
    title: "Contract Review",
    description: "Review contracts with AI to surface risky clauses, obligations, and key terms.",
    href: "/solutions/contract-review",
    color: "bg-amber-500/10 text-amber-600 group-hover:bg-amber-500 group-hover:text-white",
  },
  {
    icon: GraduationCap,
    title: "Course Search",
    description: "Find and compare courses near you by category, mode, level, and price.",
    href: "/solutions/course-search",
    color: "bg-emerald-500/10 text-emerald-600 group-hover:bg-emerald-500 group-hover:text-white",
  },
  {
    icon: ClipboardCheck,
    title: "ATS Resume Matcher",
    description: "Match your resume against job descriptions and get an ATS compatibility score.",
    href: "/solutions/ats-resume-matcher",
    color: "bg-violet-500/10 text-violet-600 group-hover:bg-violet-500 group-hover:text-white",
  },
]

/**
 * "/" is the workspace dashboard and is public — signed-out visitors see the
 * same tool list, and the tools themselves are what require a session. It lives
 * outside the (protected) route group, so it renders the navbar itself. The
 * profile/portfolio page is at /profile.
 */
export default function DashboardPage() {
  const { user, isLoading } = useAuth()
  const [greeting, setGreeting] = useState("")

  useEffect(() => {
    const h = new Date().getHours()
    if (h < 12) setGreeting("Good morning")
    else if (h < 17) setGreeting("Good afternoon")
    else setGreeting("Good evening")
  }, [])

  const name = user?.full_name?.split(" ")[0] || user?.email?.split("@")[0]

  return (
    <div className="min-h-screen bg-background">
      <WithSubnavigation />

      {/* Welcome banner. Auth resolves client-side, so hold the heading's space
          while it loads rather than flashing the signed-out copy. */}
      <div className="border-b bg-muted/30">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <p className="text-sm text-muted-foreground font-medium uppercase tracking-widest mb-1">
            {greeting}
          </p>
          {isLoading ? (
            <div className="h-9 w-72 max-w-full animate-pulse rounded bg-muted" />
          ) : (
            <h1 className="text-3xl font-bold text-foreground">
              {user ? `Welcome back, ${name}` : "Welcome to mnsAI"}
            </h1>
          )}
          <p className="mt-2 text-muted-foreground">
            {user
              ? "Here's your mnsAI workspace. Pick a tool and get started."
              : "AI tools for documents, contracts, courses, and resumes. Sign in to start using them."}
          </p>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-6 py-10 space-y-10">

        {/* Solutions */}
        <section>
          <h2 className="text-lg font-semibold text-foreground mb-4">Solutions</h2>
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {solutions.map(({ icon: Icon, title, description, href, color }) => (
              <Link key={title} href={href} className="group">
                <Card className="h-full hover:shadow-md transition-all duration-200 border border-border hover:border-ui-main/30">
                  <CardContent className="pt-6 pb-6 flex flex-col gap-3 h-full">
                    <div className={`inline-flex items-center justify-center w-10 h-10 rounded-lg transition-colors duration-200 ${color}`}>
                      <Icon className="h-5 w-5" />
                    </div>
                    <h3 className="font-semibold text-foreground">{title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed flex-1">
                      {description}
                    </p>
                    <span className="inline-flex items-center text-xs font-semibold text-ui-main group-hover:underline mt-1">
                      Open <ArrowRight className="ml-1 h-3 w-3" />
                    </span>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </section>

        {/* Coming soon */}
        <section>
          <Card className="border-dashed border-border bg-muted/20">
            <CardContent className="py-8 flex flex-col items-center text-center gap-2">
              <p className="text-sm font-medium text-foreground">More solutions coming soon</p>
              <p className="text-xs text-muted-foreground max-w-sm">
                We&apos;re continuously adding new AI tools to the platform. Check back regularly for updates.
              </p>
            </CardContent>
          </Card>
        </section>

      </div>
    </div>
  )
}
