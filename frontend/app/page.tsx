import WithSubnavigation from "@/components/common/with-subnavigation"
import { AaLeaderboard } from "@/components/dashboard/aa-leaderboard"
import { Greeting } from "@/components/dashboard/greeting"
import { LiveReadout } from "@/components/dashboard/live-readout"
import { PulseBand } from "@/components/dashboard/pulse-band"
import { ToolsGrid } from "@/components/dashboard/tools-grid"
import { WireTicker } from "@/components/dashboard/wire-ticker"
import { getTrendingModels } from "@/lib/ai-pulse/models"
import { getWireItems } from "@/lib/ai-pulse/news"
import { getNewOpenRouterModels } from "@/lib/ai-pulse/openrouter"
import { getLatestPapers } from "@/lib/ai-pulse/papers"

/**
 * "/" is the workspace dashboard and is public — an "AI operations desk".
 *
 * The page alternates two materials: warm paper for the visitor's own
 * workspace (hero, tools, benchmarks) and the dark instrument slab for
 * readings pulled from the outside world (wire ticker, live readout, AI
 * Pulse). Laid out as full-width bands rather than columns, so no section
 * has to match another's height.
 *
 * Server component with ISR (30 min) so external sources are hit a couple of
 * times per hour total, never per visitor; the auth greeting is a client
 * island. Signed-out visitors see the same page — the tools themselves are
 * what require a session. The profile/portfolio page is at /profile.
 */
export const revalidate = 1800

export default async function DashboardPage() {
  const [models, papers, wire, orModels] = await Promise.all([
    getTrendingModels(),
    getLatestPapers(),
    getWireItems(),
    getNewOpenRouterModels(),
  ])

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <WithSubnavigation />

      <WireTicker items={wire} />

      <main className="flex-1">
        {/* Hero — warm paper. The readout fills what was an empty half. */}
        <div className="dossier-dots border-b border-border bg-muted/20">
          <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-10 px-6 py-16 sm:py-20 lg:flex-row lg:items-end">
            <Greeting />
            <LiveReadout
              counts={{
                models: models.length,
                launches: orModels.length,
                papers: papers.length,
                headlines: wire.length,
              }}
            />
          </div>
        </div>

        <div className="mx-auto max-w-6xl px-6 py-16">
          <ToolsGrid />
        </div>

        <PulseBand
          models={models}
          orModels={orModels}
          papers={papers}
          wire={wire}
        />

        <div className="mx-auto max-w-6xl px-6 py-16">
          <AaLeaderboard />
        </div>
      </main>

      <footer className="border-t border-border px-6 py-8">
        <p className="mx-auto max-w-6xl text-center font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          Live data: Hugging Face · OpenRouter · Artificial Analysis · arXiv.org
          (thank you to arXiv for use of its open-access interoperability) ·
          Hacker News · vendor blogs — headlines link to their original sources
        </p>
      </footer>
    </div>
  )
}
