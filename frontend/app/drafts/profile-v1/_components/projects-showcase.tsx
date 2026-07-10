import Link from "next/link"
import { ArrowRight, ArrowUpRight } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { projects, highlights } from "./profile-data"

export function ProjectsShowcase() {
  return (
    <section id="projects" className="px-6 py-20 bg-muted/30">
      <div className="mx-auto max-w-6xl">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-bold text-foreground sm:text-4xl">
            Live proof
          </h2>
          <p className="mt-3 text-muted-foreground max-w-2xl mx-auto">
            These aren&apos;t mockups — they&apos;re working AI tools running on
            this very platform. Try them yourself.
          </p>
        </div>

        {/* Live demo cards */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map(({ icon: Icon, title, description, builtWith, href }) => (
            <Link key={title} href={href} className="group">
              <Card className="h-full hover:shadow-md transition-shadow duration-200 border border-border">
                <CardContent className="pt-6 pb-6 flex flex-col gap-3 h-full">
                  <div className="flex items-center justify-between">
                    <span className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-ui-main/10 text-ui-main group-hover:bg-ui-main group-hover:text-white transition-colors duration-200">
                      <Icon className="h-5 w-5" />
                    </span>
                    <Badge variant="secondary" className="text-[11px]">
                      Live demo
                    </Badge>
                  </div>
                  <h3 className="font-semibold text-foreground">{title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed flex-1">
                    {description}
                  </p>
                  <p className="text-xs text-muted-foreground/80">
                    <span className="font-medium text-foreground/70">
                      Built with:
                    </span>{" "}
                    {builtWith}
                  </p>
                  <span className="inline-flex items-center text-xs font-semibold text-ui-main group-hover:underline mt-1">
                    Open tool <ArrowUpRight className="ml-1 h-3.5 w-3.5" />
                  </span>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>

        {/* Experience highlights */}
        <div className="mt-16 mx-auto max-w-3xl">
          <h3 className="text-xl font-bold text-foreground text-center mb-8">
            Selected work
          </h3>
          <ul className="flex flex-col gap-4">
            {highlights.map(({ text }) => (
              <li
                key={text}
                className="flex items-start gap-3 rounded-xl border border-border bg-background px-5 py-4"
              >
                <ArrowRight className="h-4 w-4 text-ui-main shrink-0 mt-1" />
                <span className="text-sm text-muted-foreground leading-relaxed">
                  {text}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}
