import { Check } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { skillGroups } from "./profile-data"

export function SkillsGrid() {
  return (
    <section id="skills" className="px-6 py-20 bg-muted/30">
      <div className="mx-auto max-w-6xl">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-bold text-foreground sm:text-4xl">
            Skills &amp; abilities
          </h2>
          <p className="mt-3 text-muted-foreground max-w-2xl mx-auto">
            Full-stack Generative AI — from model and data work down to the APIs,
            infrastructure, and frontends that put it in production.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {skillGroups.map(({ icon: Icon, title, items }) => (
            <Card
              key={title}
              className="h-full border border-border hover:shadow-md transition-shadow duration-200"
            >
              <CardContent className="pt-6 pb-6 flex flex-col gap-4 h-full">
                <div className="flex items-center gap-3">
                  <span className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-ui-main/10 text-ui-main">
                    <Icon className="h-5 w-5" />
                  </span>
                  <h3 className="font-semibold text-foreground">{title}</h3>
                </div>
                <ul className="flex flex-col gap-2.5">
                  {items.map((item) => (
                    <li
                      key={item}
                      className="flex items-start gap-2 text-sm text-muted-foreground leading-relaxed"
                    >
                      <Check className="h-4 w-4 text-ui-main shrink-0 mt-0.5" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
