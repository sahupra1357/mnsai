import { ArrowRight, Mail } from "lucide-react"
import { profile, credentials, heroCtas } from "./profile-data"

/**
 * Typography-led hero (v2 "dossier"). No boxed card: a mono eyebrow, the name set
 * huge and tight in the display face, a large muted dek, and a byline row of
 * credential chips over a faint theme-aware dot-grid. Server component — the
 * primary CTA is a plain in-page anchor to the chat section.
 */
export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-border">
      {/* Dot-grid texture, masked so it fades before the fold */}
      <div
        aria-hidden
        className="dossier-dots dossier-dots-mask pointer-events-none absolute inset-0"
      />
      <div className="relative mx-auto max-w-6xl px-6 pb-16 pt-20 sm:pt-28">
        <div className="max-w-3xl">
          <p className="font-mono text-xs font-medium uppercase tracking-[0.2em] text-ui-accent">
            {profile.eyebrow}
          </p>

          <h1 className="mt-5 font-display text-5xl font-bold leading-[0.98] tracking-tight text-foreground sm:text-6xl lg:text-7xl">
            {profile.name}
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground sm:text-xl">
            {profile.valueProposition}
          </p>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground/80 sm:text-base">
            {profile.supportingLine}
          </p>

          {/* CTAs */}
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <a
              href="#chat"
              className="group inline-flex items-center gap-2 rounded-md bg-ui-main px-5 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#003d8f] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ui-accent"
            >
              {heroCtas.primary}
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </a>
            <a
              href={`mailto:${profile.email}`}
              className="inline-flex items-center gap-2 rounded-md border border-border bg-background px-5 py-3 text-sm font-semibold text-foreground transition-colors hover:border-ui-accent/40 hover:text-ui-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ui-accent"
            >
              <Mail className="h-4 w-4" />
              {heroCtas.secondary}
            </a>
          </div>

          {/* Credential byline */}
          <ul className="mt-10 flex flex-wrap gap-x-5 gap-y-2.5 border-t border-border/70 pt-6">
            {credentials.map((c) => {
              const Icon = c.icon
              return (
                <li
                  key={c.short}
                  title={c.full}
                  className="flex items-center gap-1.5 font-mono text-[11px] font-medium uppercase tracking-wider text-muted-foreground"
                >
                  <Icon className="h-3.5 w-3.5 text-ui-accent" />
                  {c.short}
                </li>
              )
            })}
          </ul>
        </div>
      </div>
    </section>
  )
}
