import { education, certifications, learning } from "@/lib/profile-data"

/**
 * Education & certifications in two side-by-side columns. Year fields are
 * [NEEDS INPUT] → null renders a muted "Year TBC" chip instead of a fabricated
 * date. Certification issuer monograms use a muted initial tile (no logos yet).
 */
export function EducationCerts() {
  const EduIcon = learning.educationIcon
  const CertIcon = learning.certificationsIcon

  return (
    <div className="grid gap-10 lg:grid-cols-2">
      {/* Education */}
      <div>
        <div className="mb-5 flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card text-ui-accent">
            <EduIcon className="h-4 w-4" />
          </span>
          <h3 className="font-display text-xl font-bold tracking-tight text-foreground">
            {learning.educationLabel}
          </h3>
        </div>

        <div className="space-y-4">
          {education.map((e) => (
            <div
              key={e.institution}
              className="rounded-2xl border border-border bg-card p-6 shadow-sm"
            >
              <YearChip year={e.year} />
              <p className="mt-3 font-display text-lg font-bold tracking-tight text-foreground">
                {e.degree}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                {e.institution}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Certifications */}
      <div>
        <div className="mb-5 flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card text-ui-accent">
            <CertIcon className="h-4 w-4" />
          </span>
          <h3 className="font-display text-xl font-bold tracking-tight text-foreground">
            {learning.certificationsLabel}
          </h3>
        </div>

        <ul className="divide-y divide-border overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
          {certifications.map((c) => (
            <li key={c.title} className="flex items-center gap-4 p-5">
              <div className="min-w-0 flex-1">
                <YearChip year={c.year} />
                <p className="mt-2 font-semibold text-foreground">{c.title}</p>
                <p className="text-sm text-muted-foreground">{c.issuer}</p>
              </div>
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-border bg-muted/40 font-display text-sm font-bold text-muted-foreground">
                {c.issuer.charAt(0)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

/** Year slot: renders the year, or a muted blank-year chip when null. */
function YearChip({ year }: { year: string | null }) {
  if (year) {
    return (
      <span className="font-mono text-xs font-semibold uppercase tracking-wider text-ui-accent">
        {year}
      </span>
    )
  }
  return (
    <span className="inline-block rounded border border-dashed border-border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground/70">
      {learning.blankYearLabel}
    </span>
  )
}
