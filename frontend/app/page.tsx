import WithSubnavigation from "@/components/common/with-subnavigation"
import { AaLeaderboard } from "@/components/dashboard/aa-leaderboard"
import { Greeting } from "@/components/dashboard/greeting"
import {
  FreshPapers,
  ModelWatch,
  OpenRouterWatch,
  TheWireList,
} from "@/components/dashboard/pulse-rail"
import { ToolsGrid } from "@/components/dashboard/tools-grid"
import { WireTicker } from "@/components/dashboard/wire-ticker"
import { getTrendingModels } from "@/lib/ai-pulse/models"
import { getWireItems } from "@/lib/ai-pulse/news"
import { getNewOpenRouterModels } from "@/lib/ai-pulse/openrouter"
import { getLatestPapers } from "@/lib/ai-pulse/papers"

/**
 * "/" is the workspace dashboard and is public — an "AI operations desk":
 * the AI Pulse layer (wire ticker + model watch + fresh papers) shows what's
 * moving in AI right now, and the tools grid below is the act-on-it layer.
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
  const hasRail =
    models.length > 0 ||
    papers.length > 0 ||
    wire.length > 0 ||
    orModels.length > 0

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <WithSubnavigation />

      <WireTicker items={wire} />

      <div className="border-b bg-muted/30">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <Greeting />
        </div>
      </div>

      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
        <div className="flex flex-col gap-12 lg:flex-row lg:gap-10">
          {/* Sticky so the tools desk stays in view while the longer Pulse
              rail scrolls past it on desktop. */}
          <div className="min-w-0 flex-1 lg:sticky lg:top-8 lg:self-start">
            <ToolsGrid />
          </div>

          {hasRail && (
            <aside
              className="w-full shrink-0 space-y-10 lg:w-[340px]"
              aria-label="AI Pulse — live AI intelligence"
            >
              <ModelWatch models={models} />
              <OpenRouterWatch models={orModels} />
              <FreshPapers papers={papers} />
              <TheWireList items={wire} />
            </aside>
          )}
        </div>

        {/* Full-width benchmarks section — the embedded Space needs the whole
            content width, so it sits below the tools + rail columns. */}
        <div className="mt-16">
          <AaLeaderboard />
        </div>
      </main>

      <footer className="border-t border-border px-6 py-6">
        <p className="mx-auto max-w-6xl text-center font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          Live data: Hugging Face · OpenRouter · Artificial Analysis · arXiv.org
          (thank you to arXiv for use of its open-access interoperability) ·
          Hacker News · vendor blogs — headlines link to their original sources
        </p>
      </footer>
    </div>
  )
}
