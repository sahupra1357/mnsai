import { ArrowRight } from "lucide-react"
import { services, sections, serviceCtaLabel } from "@/lib/profile-data"
import { SectionHeading } from "./section-heading"
import { ChatPrefillLink } from "./chat-prefill-link"

/**
 * Services as numbered editorial blocks (v2 design move 5): big muted ordinal +
 * bold offer name + description + "Discuss this →" chat pre-fill link. A stacked
 * list separated by hairlines — not a uniform card grid.
 */
export function Services() {
  const meta = sections.services
  return (
    <section id={meta.id} className="scroll-mt-24">
      <SectionHeading meta={meta} />

      <ol className="divide-y divide-border border-t border-border">
        {services.map(({ icon: Icon, title, description, prefill }, i) => (
          <li
            key={title}
            className="grid grid-cols-[auto_1fr] gap-x-5 gap-y-2 py-7 sm:gap-x-7"
          >
            <span className="font-mono text-sm font-medium text-ui-accent">
              {String(i + 1).padStart(2, "0")}
            </span>
            <div>
              <div className="flex items-center gap-2.5">
                <Icon className="h-5 w-5 shrink-0 text-ui-accent" />
                <h3 className="font-display text-xl font-semibold tracking-tight text-foreground">
                  {title}
                </h3>
              </div>
              <p className="mt-2.5 max-w-xl text-[15px] leading-relaxed text-muted-foreground">
                {description}
              </p>
              <ChatPrefillLink
                question={prefill}
                className="group mt-3 inline-flex items-center gap-1 text-sm font-semibold text-ui-accent hover:underline"
              >
                {serviceCtaLabel}
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </ChatPrefillLink>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
