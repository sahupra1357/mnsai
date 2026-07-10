import { skillGroups, sections } from "@/lib/profile-data"
import { SectionHeading } from "./section-heading"

/**
 * Skills as compact definition lists (design move 7): two-column group blocks
 * (one on mobile) with a small icon + group name + tight item list. Typography
 * over card chrome — hairline separators only.
 */
export function SkillsGrid() {
  const meta = sections.toolbox
  return (
    <section id={meta.id} className="scroll-mt-24">
      <SectionHeading meta={meta} />

      <div className="grid grid-cols-1 gap-x-10 gap-y-8 sm:grid-cols-2">
        {skillGroups.map(({ icon: Icon, title, items }) => (
          <div key={title} className="border-t border-border pt-4">
            <div className="flex items-center gap-2.5">
              <Icon className="h-4 w-4 shrink-0 text-ui-accent" />
              <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-foreground">
                {title}
              </h3>
            </div>
            <ul className="mt-3 space-y-2">
              {items.map((item) => (
                <li
                  key={item}
                  className="flex gap-2.5 text-sm leading-relaxed text-muted-foreground"
                >
                  <span
                    className="mt-2 h-1 w-1 shrink-0 rounded-full bg-ui-accent/60"
                    aria-hidden
                  />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  )
}
