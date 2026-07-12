import type { SectionMeta } from "@/lib/profile-data"

/**
 * H2 section header: a small brand icon tile beside the heading, with the
 * subtitle below. Copy and icon come from the section metadata in profile-data.
 */
export function SectionHeading({ meta }: { meta: SectionMeta }) {
  const Icon = meta.icon
  return (
    <div className="mb-10">
      <div className="flex items-center gap-3">
        <span className="flex h-11 w-11 items-center justify-center rounded-xl border border-border bg-card text-ui-accent shadow-sm">
          <Icon className="h-5 w-5" />
        </span>
        <h2 className="font-display text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
          {meta.heading}
        </h2>
      </div>
      <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground">
        {meta.subtitle}
      </p>
    </div>
  )
}
