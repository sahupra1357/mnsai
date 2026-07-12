import type { LucideIcon } from "lucide-react"
import type { FeaturedBullet, FeaturedStat } from "@/lib/profile-data"

/**
 * Wide feature panel used for the flagship work entry and the platform project.
 * Left column: icon tile, badge, title, description, icon-bullet list. Right
 * column (optional): a stack of stat tiles. Optional tech chips + a CTA slot in
 * the footer (a caller-supplied node, e.g. a client "open chat" button).
 * Reference-format only — all copy comes from profile-data.
 */
export function FeaturedPanel({
  icon: Icon,
  badge,
  title,
  description,
  bullets,
  stats,
  chips,
  ctaSlot,
}: {
  icon: LucideIcon
  badge: string
  title: string
  description: string
  bullets: readonly FeaturedBullet[]
  stats?: readonly FeaturedStat[]
  chips?: readonly string[]
  ctaSlot?: React.ReactNode
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-card to-muted/20 p-6 shadow-sm sm:p-8">
      <div className="grid gap-8 lg:grid-cols-[1.6fr_1fr]">
        {/* Content */}
        <div>
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-ui-accent/10 text-ui-accent">
              <Icon className="h-5 w-5" />
            </span>
            <span className="rounded-full bg-ui-accent/10 px-3 py-1 font-mono text-[11px] font-semibold uppercase tracking-wider text-ui-accent">
              {badge}
            </span>
          </div>

          <h3 className="mt-5 font-display text-2xl font-bold tracking-tight text-foreground">
            {title}
          </h3>
          <p className="mt-3 max-w-xl text-base leading-relaxed text-muted-foreground">
            {description}
          </p>

          <ul className="mt-6 space-y-3">
            {bullets.map((b) => {
              const BIcon = b.icon
              return (
                <li key={b.text} className="flex items-start gap-3">
                  <BIcon className="mt-0.5 h-4 w-4 shrink-0 text-ui-accent" />
                  <span className="text-sm leading-relaxed text-foreground">
                    {b.text}
                  </span>
                </li>
              )
            })}
          </ul>

          {chips && chips.length > 0 && (
            <ul className="mt-6 flex flex-wrap gap-2">
              {chips.map((c) => (
                <li
                  key={c}
                  className="rounded-md border border-border bg-background px-2.5 py-1 font-mono text-xs text-muted-foreground"
                >
                  {c}
                </li>
              ))}
            </ul>
          )}

          {ctaSlot && <div className="mt-6">{ctaSlot}</div>}
        </div>

        {/* Stat tiles */}
        {stats && stats.length > 0 && (
          <div className="flex flex-col gap-3">
            {stats.map((s) => (
              <div
                key={s.label}
                className="flex flex-col items-center justify-center rounded-xl border border-border bg-background px-4 py-5 text-center"
              >
                <span className="font-display text-3xl font-bold tracking-tight text-ui-accent">
                  {s.value}
                </span>
                <span className="mt-1 text-xs font-medium text-muted-foreground">
                  {s.label}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
