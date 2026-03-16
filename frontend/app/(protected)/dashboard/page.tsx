"use client"

import Link from "next/link"
import useAuth from "@/hooks/use-auth"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  FileText,
  GraduationCap,
  ClipboardCheck,
  ArrowRight,
  LayoutDashboard,
  Settings,
  Users,
} from "lucide-react"

const solutions = [
  {
    icon: FileText,
    title: "Data Extraction",
    description: "Extract structured data from PDFs, invoices, and scanned documents using AI.",
    href: "/extractor",
    color: "bg-blue-500/10 text-blue-600 group-hover:bg-blue-500 group-hover:text-white",
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

const quickLinks = [
  { icon: Settings, label: "Account Settings", href: "/settings" },
  { icon: LayoutDashboard, label: "Items", href: "/items" },
  { icon: Users, label: "Admin Panel", href: "/admin", superuserOnly: true },
]

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return "Good morning"
  if (h < 17) return "Good afternoon"
  return "Good evening"
}

export default function DashboardPage() {
  const { user } = useAuth()

  const name = user?.full_name?.split(" ")[0] || user?.email?.split("@")[0] || "there"

  return (
    <div className="min-h-screen bg-background">
      {/* Welcome banner */}
      <div className="border-b bg-muted/30">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <p className="text-sm text-muted-foreground font-medium uppercase tracking-widest mb-1">
            {greeting()}
          </p>
          <h1 className="text-3xl font-bold text-foreground">
            Welcome back, {name}
          </h1>
          <p className="mt-2 text-muted-foreground">
            Here&apos;s your mnsAI workspace. Pick a tool and get started.
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

        {/* Quick links */}
        <section>
          <h2 className="text-lg font-semibold text-foreground mb-4">Quick Links</h2>
          <div className="flex flex-wrap gap-3">
            {quickLinks
              .filter((l) => !l.superuserOnly || user?.is_superuser)
              .map(({ icon: Icon, label, href }) => (
                <Button key={label} asChild variant="outline" size="sm" className="gap-2">
                  <Link href={href}>
                    <Icon className="h-4 w-4" />
                    {label}
                  </Link>
                </Button>
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
