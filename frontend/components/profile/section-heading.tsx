import type { SectionMeta } from "@/lib/profile-data"

/**
 * Left-aligned editorial section header (v2). Renders a mono section index +
 * nav label kicker, the question-form heading, and a muted subtitle — all from
 * the typed SectionMeta so no copy lives in JSX.
 */
export function SectionHeading({ meta }: { meta: SectionMeta }) {
  return (
    <header className="mb-10">
      <div className="flex items-center gap-3 font-mono text-[11px] uppercase tracking-[0.18em] text-ui-accent">
        <span>§{meta.index}</span>
        <span className="h-px w-6 bg-ui-accent/40" aria-hidden />
        <span className="text-muted-foreground">{meta.navLabel}</span>
      </div>
      <h2 className="mt-4 font-display text-3xl font-bold tracking-tight text-foreground sm:text-[2.5rem] sm:leading-[1.1]">
        {meta.heading}
      </h2>
      <p className="mt-3 max-w-2xl text-base leading-relaxed text-muted-foreground">
        {meta.subtitle}
      </p>
    </header>
  )
}
