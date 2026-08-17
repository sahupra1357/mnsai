import type { OpenRouterModel } from "@/lib/ai-pulse/openrouter"
import type { Paper, TrendingModel, WireItem } from "@/lib/ai-pulse/types"

/**
 * AI Pulse modules — the readings shown on the instrument band. Everything is
 * text and links in mono/aqua on the dark slab; no thumbnails, no reproduced
 * body content. Each module renders nothing when its source returned no data,
 * so an outage quietly removes a column instead of showing an error.
 */

function ModuleHeading({
  title,
  source,
  sourceHref,
}: {
  title: string
  source: string
  /** When set, the source label links out (e.g. to a leaderboard we can't embed) */
  sourceHref?: string
}) {
  return (
    <div className="mb-5 flex items-baseline justify-between gap-3 border-b pb-2.5 inst-rule">
      <h3 className="font-mono text-[11px] font-semibold uppercase tracking-[0.22em]">
        {title}
      </h3>
      {sourceHref ? (
        <a
          href={sourceHref}
          target="_blank"
          rel="noopener noreferrer"
          className="font-mono text-[10px] uppercase tracking-wider inst-accent hover:underline"
        >
          {source} ↗
        </a>
      ) : (
        <span className="font-mono text-[10px] uppercase tracking-wider inst-dim">
          {source}
        </span>
      )}
    </div>
  )
}

function formatCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`
  return String(n)
}

function formatDate(iso?: string): string {
  if (!iso) return ""
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ""
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
}

export function ModelWatch({ models }: { models: TrendingModel[] }) {
  if (models.length === 0) return null
  const max = Math.max(...models.map((m) => m.downloads), 1)

  return (
    <section aria-label="Trending AI models">
      <ModuleHeading title="Model Watch" source="Hugging Face" />
      <ol className="space-y-3.5">
        {models.map((m, i) => (
          <li key={m.id}>
            <a
              href={m.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group block"
            >
              <div className="flex items-baseline gap-2.5">
                <span className="w-4 shrink-0 font-mono text-[10px] tabular-nums inst-dim">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="min-w-0 flex-1 truncate text-[13px] font-medium group-hover:underline">
                  {m.name}
                </span>
                {/* Downloads carry the scale contrast in this module — the one
                    number worth reading from across the room. */}
                <span className="shrink-0 font-mono text-sm font-semibold tabular-nums inst-accent">
                  {formatCount(m.downloads)}
                </span>
              </div>
              <div className="ml-6 mt-1.5 flex items-center gap-2">
                <div
                  className="inst-bar h-[3px] rounded-full opacity-50 transition-opacity group-hover:opacity-100"
                  style={{
                    width: `${Math.max((m.downloads / max) * 100, 4)}%`,
                  }}
                  aria-hidden="true"
                />
                <span className="truncate font-mono text-[10px] inst-dim">
                  {m.org}
                </span>
              </div>
            </a>
          </li>
        ))}
      </ol>
    </section>
  )
}

function formatPrice(perM: number): string {
  if (perM === 0) return "free"
  return perM < 1
    ? `$${perM.toFixed(2)}`
    : `$${perM.toFixed(perM < 10 ? 2 : 0)}`
}

function formatContext(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M ctx`
  if (tokens >= 1_000) return `${Math.round(tokens / 1_000)}k ctx`
  return tokens > 0 ? `${tokens} ctx` : ""
}

export function OpenRouterWatch({ models }: { models: OpenRouterModel[] }) {
  if (models.length === 0) return null

  return (
    <section aria-label="Newest models on OpenRouter">
      {/* Usage rankings can't be embedded (frame-ancestors 'self') and their
          data endpoint is undocumented — so we show the documented catalog's
          newest launches and link out to the leaderboard itself. */}
      <ModuleHeading
        title="New on OpenRouter"
        source="weekly rankings"
        sourceHref="https://openrouter.ai/rankings"
      />
      <ul className="space-y-3.5">
        {models.map((m) => (
          <li key={m.id}>
            <a
              href={m.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group block"
            >
              <div className="flex items-baseline gap-2.5">
                <span className="min-w-0 flex-1 truncate text-[13px] font-medium group-hover:underline">
                  {m.name}
                </span>
                <span className="shrink-0 font-mono text-[10px] inst-dim">
                  {formatDate(new Date(m.created * 1000).toISOString())}
                </span>
              </div>
              <div className="mt-1 flex items-center gap-2 font-mono text-[10px] inst-dim">
                {m.contextLength > 0 && (
                  <span>{formatContext(m.contextLength)}</span>
                )}
                <span>
                  {formatPrice(m.promptPerM)}
                  {m.promptPerM > 0 &&
                    ` / ${formatPrice(m.completionPerM)} per M`}
                </span>
              </div>
            </a>
          </li>
        ))}
      </ul>
    </section>
  )
}

export function FreshPapers({ papers }: { papers: Paper[] }) {
  if (papers.length === 0) return null

  return (
    <section aria-label="Latest AI research papers">
      <ModuleHeading title="Fresh Papers" source="arXiv" />
      <ul className="space-y-4">
        {papers.slice(0, 5).map((p) => (
          <li key={p.url}>
            <a
              href={p.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group block"
            >
              <div className="mb-1.5 flex items-center gap-2">
                <span className="rounded-sm px-1.5 py-0.5 font-mono text-[10px] font-medium inst-accent ring-1 ring-inset ring-[hsl(var(--inst-line))]">
                  {p.category}
                </span>
                <span className="font-mono text-[10px] inst-dim">
                  {formatDate(p.published)}
                </span>
              </div>
              <p className="text-[13px] font-medium leading-snug group-hover:underline">
                {p.title}
              </p>
              <p className="mt-1 truncate text-[11px] inst-dim">
                {p.authors.slice(0, 3).join(", ")}
                {p.authors.length > 3 ? " et al." : ""}
              </p>
            </a>
          </li>
        ))}
      </ul>
    </section>
  )
}

/**
 * The Wire as a readable row across the foot of the band — the ticker above
 * is for glancing, this is for actually reading. Three across, so it breaks
 * the vertical rhythm of the three columns above it.
 */
export function WireRow({ items }: { items: WireItem[] }) {
  if (items.length === 0) return null

  return (
    <section aria-label="Latest AI news headlines">
      <ModuleHeading title="The Wire" source="HN · vendor blogs" />
      <ul className="grid gap-x-8 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.slice(0, 6).map((item) => (
          <li key={item.url}>
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group flex items-baseline gap-2.5"
            >
              <span className="inst-accent opacity-60" aria-hidden="true">
                ▸
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-[13px] leading-snug group-hover:underline">
                  {item.title}
                </span>
                <span className="mt-1 block font-mono text-[10px] uppercase tracking-wider inst-dim">
                  {item.source}
                  {formatDate(item.publishedAt) &&
                    ` · ${formatDate(item.publishedAt)}`}
                </span>
              </span>
            </a>
          </li>
        ))}
      </ul>
    </section>
  )
}
