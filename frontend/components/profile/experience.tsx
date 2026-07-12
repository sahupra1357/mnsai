import { Building2 } from "lucide-react"
import {
  experienceEntries,
  experience,
  selectedWork,
  featuredWork,
} from "@/lib/profile-data"
import { PlaceholderCard } from "./placeholder-card"
import { FeaturedPanel } from "./featured-panel"

/**
 * Work experience. The resume has no employer names or dates, so `experienceEntries`
 * is empty → one dashed placeholder entry renders in place of a named role. The
 * real accomplishments render below as an unattributed "Selected work" list, plus
 * a blank corporate-clients strip and the renderable featured-work panel.
 */
export function Experience() {
  return (
    <div className="space-y-10">
      {/* Employer entry — placeholder until names/dates are confirmed */}
      {experienceEntries.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border/80 bg-muted/20 p-6 sm:p-8">
          <div className="flex items-start gap-4">
            <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-dashed border-border text-muted-foreground/70">
              <Building2 className="h-5 w-5" />
            </span>
            <div>
              <p className="font-display text-lg font-semibold text-foreground/80">
                {experience.placeholderTitle}
              </p>
              <p className="mt-1.5 max-w-xl text-sm leading-relaxed text-muted-foreground">
                {experience.placeholderBody}
              </p>
            </div>
          </div>
        </div>
      ) : null}

      {/* Selected work — unattributed accomplishment bullets */}
      <div>
        <p className="mb-4 font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-ui-accent">
          {experience.selectedWorkLabel}
        </p>
        <ul className="space-y-4">
          {selectedWork.map((item) => (
            <li
              key={item.lead}
              className="rounded-xl border border-border bg-card p-5 shadow-sm"
            >
              <p className="text-sm leading-relaxed text-foreground">
                <span className="font-semibold text-foreground">
                  {item.lead}.{" "}
                </span>
                <span className="text-muted-foreground">{item.body}</span>
              </p>
            </li>
          ))}
        </ul>
      </div>

      {/* Corporate clients — blank placeholder strip */}
      <div>
        <p className="mb-4 font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground/70">
          {experience.clientsLabel}
        </p>
        {experience.clients.length === 0 ? (
          <PlaceholderCard label={experience.clientsPlaceholder} className="min-h-0 py-6" />
        ) : (
          <ul className="flex flex-wrap items-center gap-6">
            {experience.clients.map((c) => (
              <li key={c.name} className="text-sm font-semibold text-muted-foreground">
                {c.name}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Featured-work panel with stat tiles */}
      <FeaturedPanel
        icon={featuredWork.icon}
        badge={featuredWork.badge}
        title={featuredWork.title}
        description={featuredWork.description}
        bullets={featuredWork.bullets}
        stats={featuredWork.stats}
      />
    </div>
  )
}
