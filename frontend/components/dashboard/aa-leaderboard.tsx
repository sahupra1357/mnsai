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
      <div className="mb-6 flex items-baseline justify-between gap-4 border-b border-border pb-3">
        <h2 className="font-display text-2xl font-bold tracking-tight text-foreground">
          Benchmarks
        </h2>
        <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          Independent · third-party
        </p>
      </div>

      {/* The embed is somebody else's screen, so it gets a bezel: an
          instrument header bar naming the source, with the Space itself as
          the display below it. Without the bar the white iframe reads as a
          hole punched in the page. */}
      <div className="overflow-hidden rounded-xl border border-border shadow-sm">
        <div className="instrument flex items-center justify-between gap-3 px-5 py-3">
          <span className="flex items-center gap-2.5 font-mono text-[11px] font-semibold uppercase tracking-[0.22em]">
            <span
              className="inst-live-dot h-1.5 w-1.5 animate-pulse rounded-full"
              aria-hidden="true"
            />
            LLM Performance Leaderboard
          </span>
          <a
            href={SPACE_PAGE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 font-mono text-[10px] uppercase tracking-wider inst-accent hover:underline"
          >
            Artificial Analysis ↗
          </a>
        </div>

        <iframe
          src={SPACE_EMBED_URL}
          title="Artificial Analysis LLM Performance Leaderboard"
          loading="lazy"
          className="block h-[640px] w-full border-0 bg-white sm:h-[720px]"
          sandbox="allow-scripts allow-same-origin allow-popups"
        />
      </div>

      <p className="mt-3 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
        Benchmarks by Artificial Analysis, embedded from their Hugging Face
        Space
      </p>
    </section>
  )
}
