import { highlights, sections } from "@/lib/profile-data"
import { SectionHeading } from "./section-heading"

/**
 * Experience highlights as a numbered narrative list (v2 design move 6) — the
 * proof spine of the page. Bold lead-in phrase then plain text, indexed with a
 * mono ordinal. No cards; typography and a hairline ledger carry it.
 */
export function Highlights() {
  const meta = sections.work
  return (
    <section id={meta.id} className="scroll-mt-24">
      <SectionHeading meta={meta} />

      <ol className="border-t border-border">
        {highlights.map(({ lead, body }, i) => (
          <li
            key={lead}
            className="grid grid-cols-[auto_1fr] gap-x-5 border-b border-border py-6 sm:gap-x-7"
          >
            <span className="pt-0.5 font-mono text-sm font-medium tabular-nums text-ui-accent">
              {String(i + 1).padStart(2, "0")}
            </span>
            <p className="text-[15px] leading-relaxed text-muted-foreground">
              <span className="font-semibold text-foreground">{lead}</span>{" "}
              {body}
            </p>
          </li>
        ))}
      </ol>
    </section>
  )
}
