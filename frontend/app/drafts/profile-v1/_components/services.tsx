import { ArrowRight } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { services } from "./profile-data"
import { ChatPrefillLink } from "./chat-prefill-link"

export function Services() {
  return (
    <section id="services" className="px-6 py-20">
      <div className="mx-auto max-w-6xl">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-bold text-foreground sm:text-4xl">
            What I can build for you
          </h2>
          <p className="mt-3 text-muted-foreground max-w-2xl mx-auto">
            Engagements focused on outcomes — from a first proof of concept to a
            production system your team can run.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          {services.map(({ icon: Icon, title, description, prefill }) => (
            <Card
              key={title}
              className="h-full border border-border hover:shadow-md transition-shadow duration-200"
            >
              <CardContent className="pt-6 pb-6 flex flex-col gap-3 h-full">
                <span className="inline-flex items-center justify-center w-11 h-11 rounded-lg bg-ui-main/10 text-ui-main">
                  <Icon className="h-5 w-5" />
                </span>
                <h3 className="font-semibold text-foreground text-lg">
                  {title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed flex-1">
                  {description}
                </p>
                <ChatPrefillLink
                  question={prefill}
                  className="inline-flex items-center self-start text-sm font-semibold text-ui-main hover:underline mt-2"
                >
                  Discuss this project
                  <ArrowRight className="ml-1 h-4 w-4" />
                </ChatPrefillLink>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
