import type { OpenRouterModel } from "@/lib/ai-pulse/openrouter"
import type { Paper, TrendingModel, WireItem } from "@/lib/ai-pulse/types"
import {
  FreshPapers,
  ModelWatch,
  OpenRouterWatch,
  WireRow,
} from "./pulse-modules"

/**
 * AI Pulse — the full-width instrument band. Readings from the outside world
 * sit on the dark slab; the workspace above and below stays warm paper. Three
 * columns of vertical lists, then the wire as a horizontal row so the band
 * has its own internal rhythm rather than four identical stacks.
 */
export function PulseBand({
  models,
  orModels,
  papers,
  wire,
}: {
  models: TrendingModel[]
  orModels: OpenRouterModel[]
  papers: Paper[]
  wire: WireItem[]
}) {
  const columns = [
    models.length > 0 && <ModelWatch key="models" models={models} />,
    orModels.length > 0 && <OpenRouterWatch key="or" models={orModels} />,
    papers.length > 0 && <FreshPapers key="papers" papers={papers} />,
  ].filter(Boolean)

  if (columns.length === 0 && wire.length === 0) return null

  // The hairline edges keep the slab legible as a discrete band in dark mode,
  // where the page around it is dark too.
  return (
    <section
      className="instrument border-y inst-rule"
      aria-label="AI Pulse — live AI intelligence"
    >
      <div className="mx-auto max-w-6xl px-6 py-14 sm:py-16">
        <div className="mb-10 flex items-baseline justify-between gap-4">
          <h2 className="font-display text-2xl font-bold tracking-tight">
            AI Pulse
          </h2>
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] inst-dim">
            What&apos;s moving right now
          </p>
        </div>

        {columns.length > 0 && (
          <div className="grid gap-x-10 gap-y-12 md:grid-cols-2 lg:grid-cols-3">
            {columns}
          </div>
        )}

        {wire.length > 0 && (
          <div className="mt-14 border-t pt-10 inst-rule">
            <WireRow items={wire} />
          </div>
        )}
      </div>
    </section>
  )
}
