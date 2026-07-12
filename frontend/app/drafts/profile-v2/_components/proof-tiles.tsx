import { proofTiles } from "./profile-data"

/**
 * A 4-up band of stat tiles (big number + small mono label). Every number is
 * countable from docs/profile-draft.md — see `proofTiles` in profile-data.ts.
 * Collapses 4 → 2 → 1 across breakpoints. Each tile carries a short ui-accent
 * ledger rule to reinforce the "dossier" feel.
 */
export function ProofTiles() {
  return (
    <section className="border-b border-border bg-muted/20">
      <div className="mx-auto grid max-w-6xl grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        {proofTiles.map((tile) => (
          <div
            key={tile.label}
            className="border-b border-border px-6 py-7 last:border-b-0 sm:[&:nth-last-child(-n+2)]:border-b-0 sm:odd:border-r sm:border-border lg:border-b-0 lg:border-r lg:last:border-r-0 lg:py-9"
          >
            <div className="mb-3 h-1 w-8 rounded-full bg-ui-accent" aria-hidden />
            <div className="font-display text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
              {tile.value}
            </div>
            <div className="mt-1.5 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {tile.label}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
