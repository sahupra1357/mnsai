/**
 * Live readout — the hero's right-hand instrument panel. Fills what was an
 * empty half of the hero band with something that earns the page's "live"
 * claim: what was pulled, and when.
 *
 * The timestamp is the ISR build time, not request time — which is exactly
 * what we want it to say, since that's when this data was actually fetched.
 * Rendered in UTC so a cached page never shows a misleading local time.
 */
export function LiveReadout({
  counts,
}: {
  counts: {
    models: number
    launches: number
    papers: number
    headlines: number
  }
}) {
  const rows: [string, number][] = [
    ["models trending", counts.models],
    ["new launches", counts.launches],
    ["papers", counts.papers],
    ["headlines", counts.headlines],
  ]
  const stamp = new Date().toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  })

  return (
    <div className="instrument w-full rounded-lg p-5 sm:w-[19rem]">
      <div className="mb-4 flex items-center gap-2.5 border-b pb-3 inst-rule">
        <span
          className="inst-live-dot h-1.5 w-1.5 animate-pulse rounded-full"
          aria-hidden="true"
        />
        <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.22em] inst-accent">
          Live feed
        </span>
      </div>

      <dl className="space-y-2.5">
        {rows.map(([label, value]) => (
          <div
            key={label}
            className="flex items-baseline justify-between gap-3"
          >
            <dt className="font-mono text-[11px] uppercase tracking-wider inst-dim">
              {label}
            </dt>
            <dd className="font-mono text-lg font-semibold tabular-nums">
              {value}
            </dd>
          </div>
        ))}
      </dl>

      <p className="mt-4 border-t pt-3 font-mono text-[10px] uppercase tracking-wider inst-dim inst-rule">
        Fetched {stamp} UTC · refreshes every 30 min
      </p>
    </div>
  )
}
