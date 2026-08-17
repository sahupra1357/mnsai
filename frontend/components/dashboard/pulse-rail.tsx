import type { OpenRouterModel } from "@/lib/ai-pulse/openrouter"
import type { Paper, TrendingModel, WireItem } from "@/lib/ai-pulse/types"

/**
 * AI Pulse rail — Model Watch, Fresh Papers, and The Wire as quiet
 * typographic modules. Everything is text + links in the brand teal;
 * no thumbnails, no reproduced body content. Each module renders nothing
 * when its source returned no data.
 */

function RailHeading({
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
    <div className="mb-4 flex items-baseline justify-between gap-3 border-b border-border pb-2">
      <h2 className="flex items-center gap-2 font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-foreground">
        <span className="h-2 w-2 rounded-[1px] bg-ui-main" aria-hidden="true" />
        {title}
      </h2>
      {sourceHref ? (
        <a
          href={sourceHref}
          target="_blank"
          rel="noopener noreferrer"
          className="font-mono text-[10px] uppercase tracking-wider text-ui-accent hover:underline"
        >
          {source} ↗
        </a>
      ) : (
        <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
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
      <RailHeading title="Model Watch" source="Hugging Face" />
      <ol className="space-y-3">
        {models.map((m, i) => (
          <li key={m.id}>
            <a
              href={m.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group block"
            >
              <div className="flex items-baseline gap-2">
                <span className="w-5 shrink-0 font-mono text-[11px] tabular-nums text-muted-foreground">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="min-w-0 flex-1 truncate text-sm font-medium text-foreground group-hover:text-ui-accent group-hover:underline">
                  {m.name}
                </span>
                <span className="shrink-0 font-mono text-[11px] tabular-nums text-muted-foreground">
                  {formatCount(m.downloads)} ↓
                </span>
              </div>
              <div className="ml-7 mt-1 flex items-center gap-2">
                {/* Teal ramp: bar length = downloads relative to the leader */}
                <div
                  className="h-1 rounded-full bg-ui-main/70 transition-colors group-hover:bg-ui-main"
                  style={{
                    width: `${Math.max((m.downloads / max) * 100, 4)}%`,
                  }}
                  aria-hidden="true"
                />
                <span className="truncate font-mono text-[10px] text-muted-foreground">
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
      <RailHeading
        title="New on OpenRouter"
        source="weekly rankings"
        sourceHref="https://openrouter.ai/rankings"
      />
      <ul className="space-y-3">
        {models.map((m) => (
          <li key={m.id}>
            <a
              href={m.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group block"
            >
              <div className="flex items-baseline gap-2">
                <span className="min-w-0 flex-1 truncate text-sm font-medium text-foreground group-hover:text-ui-accent group-hover:underline">
                  {m.name}
                </span>
                <span className="shrink-0 font-mono text-[10px] text-muted-foreground">
                  {formatDate(new Date(m.created * 1000).toISOString())}
                </span>
              </div>
              <div className="mt-0.5 flex items-center gap-2 font-mono text-[10px] text-muted-foreground">
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
      <RailHeading title="Fresh Papers" source="arXiv" />
      <ul className="space-y-4">
        {papers.slice(0, 5).map((p) => (
          <li key={p.url}>
            <a
              href={p.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group block"
            >
              <div className="mb-1 flex items-center gap-2">
                <span className="rounded-sm bg-ui-main/10 px-1.5 py-0.5 font-mono text-[10px] font-medium text-ui-accent">
                  {p.category}
                </span>
                <span className="font-mono text-[10px] text-muted-foreground">
                  {formatDate(p.published)}
                </span>
              </div>
              <p className="text-sm font-medium leading-snug text-foreground group-hover:text-ui-accent group-hover:underline">
                {p.title}
              </p>
              <p className="mt-0.5 truncate text-xs text-muted-foreground">
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

/** Static, fully accessible list of the same headlines the ticker scrolls. */
export function TheWireList({ items }: { items: WireItem[] }) {
  if (items.length === 0) return null

  return (
    <section aria-label="Latest AI news headlines">
      <RailHeading title="The Wire" source="HN · vendor blogs" />
      <ul className="space-y-2.5">
        {items.slice(0, 6).map((item) => (
          <li key={item.url} className="flex items-baseline gap-2">
            <span className="text-ui-accent/70" aria-hidden="true">
              ▸
            </span>
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="min-w-0 flex-1 text-sm leading-snug text-foreground hover:text-ui-accent hover:underline"
            >
              {item.title}
            </a>
            <span className="shrink-0 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              {formatDate(item.publishedAt) || item.source}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
