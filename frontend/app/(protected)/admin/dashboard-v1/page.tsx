import { notFound } from "next/navigation"
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
import { getServerUser } from "@/lib/server-auth"

/**
 * BACKUP — frozen copy of the original "/" workspace dashboard ("AI operations
 * desk"), preserved when "/" became the AI engineering knowledge hub
 * (2026-10-14). Never edit; restore by copying back to app/page.tsx (re-add
 * <WithSubnavigation /> and `export const revalidate = 1800`).
 *
 * Superuser-only: middleware already requires a session under /admin, and the
 * backend-verified check below 404s everyone else, so the page's existence
 * isn't advertised. Differences from the original are only what living here
 * requires — the (protected) layout supplies the nav, and the per-request
 * auth check makes the route dynamic (the external feeds keep their own
 * fetch-level caching).
 */
export default async function DashboardV1BackupPage() {
  const user = await getServerUser()
  if (!user?.is_superuser) notFound()

  const [models, papers, wire, orModels] = await Promise.all([
    getTrendingModels(),
    getLatestPapers(),
    getWireItems(),
    getNewOpenRouterModels(),
  ])

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <WireTicker items={wire} />

      <div className="flex-1">
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
      </div>

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
