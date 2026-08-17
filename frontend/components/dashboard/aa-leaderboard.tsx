/**
 * LLM Performance Leaderboard — Artificial Analysis's own Hugging Face Space,
 * embedded via HF's sanctioned Space-embedding mechanism (*.static.hf.space
 * serves without frame-ancestors restrictions; every Space has an official
 * "Embed this Space" affordance). We frame it as-published with attribution —
 * no scraping, no keys. loading="lazy" defers the fetch until scrolled into
 * view. The Space keeps its own light styling in both themes; the bordered
 * card contains that visual break.
 */
const SPACE_EMBED_URL =
  "https://artificialanalysis-llm-performance-leaderboard.static.hf.space/index.html"
const SPACE_PAGE_URL =
  "https://huggingface.co/spaces/ArtificialAnalysis/LLM-Performance-Leaderboard"

export function AaLeaderboard() {
  return (
    <section aria-label="LLM performance leaderboard">
      <div className="mb-4 flex items-baseline justify-between gap-3 border-b border-border pb-2">
        <h2 className="flex items-center gap-2 font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-foreground">
          <span
            className="h-2 w-2 rounded-[1px] bg-ui-main"
            aria-hidden="true"
          />
          LLM Performance Leaderboard
        </h2>
        <a
          href={SPACE_PAGE_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="font-mono text-[10px] uppercase tracking-wider text-ui-accent hover:underline"
        >
          Artificial Analysis · Hugging Face ↗
        </a>
      </div>

      <div className="overflow-hidden rounded-lg border border-border bg-white">
        <iframe
          src={SPACE_EMBED_URL}
          title="Artificial Analysis LLM Performance Leaderboard"
          loading="lazy"
          className="h-[640px] w-full border-0 sm:h-[720px]"
          sandbox="allow-scripts allow-same-origin allow-popups"
        />
      </div>

      <p className="mt-2 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
        Independent benchmarks by Artificial Analysis, embedded from their
        Hugging Face Space
      </p>
    </section>
  )
}
