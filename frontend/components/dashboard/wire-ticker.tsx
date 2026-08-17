import type { WireItem } from "@/lib/ai-pulse/types"

/**
 * The Wire — the dashboard's signature element. A thin trading-desk tape of
 * AI headlines directly under the navbar: JetBrains Mono, brand teal accents,
 * slow CSS marquee. Server component; the motion is pure CSS so it costs no
 * JS. Pauses on hover/focus, and prefers-reduced-motion gets a static strip.
 * The full accessible list of the same items lives in <TheWireList>.
 */
/** Shared by the real links and their inert visual echo so both measure the
 *  same width — the -50% loop only lands seamlessly if the halves match. */
const itemClass =
  "group flex shrink-0 items-baseline gap-2 px-5 py-2 font-mono text-[12px] text-foreground/80 hover:text-ui-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"

export function WireTicker({ items }: { items: WireItem[] }) {
  if (items.length === 0) return null

  return (
    <div className="wire-ticker relative overflow-hidden border-b border-border bg-card/60">
      <style>{`
        @keyframes wire-scroll {
          from { transform: translateX(0); }
          to { transform: translateX(-50%); }
        }
        .wire-track {
          animation: wire-scroll ${Math.max(items.length * 6, 40)}s linear infinite;
          width: max-content;
        }
        .wire-ticker:hover .wire-track,
        .wire-ticker:focus-within .wire-track {
          animation-play-state: paused;
        }
        @media (prefers-reduced-motion: reduce) {
          .wire-track { animation: none; }
        }
      `}</style>

      <div className="flex items-stretch">
        <div className="z-10 flex shrink-0 items-center gap-2 border-r border-border bg-background px-4 py-2">
          <span
            className="h-2 w-2 animate-pulse rounded-[1px] bg-ui-main"
            aria-hidden="true"
          />
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-ui-accent">
            AI Wire
          </span>
        </div>

        <div className="relative flex-1 overflow-hidden">
          <div className="wire-track flex items-center">
            {/* Real links — the only copy in the a11y tree and tab order. */}
            {items.map((item) => (
              <a
                key={item.url}
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className={itemClass}
              >
                <span className="text-ui-accent/70" aria-hidden="true">
                  ▸
                </span>
                <span className="max-w-[34rem] truncate group-hover:underline">
                  {item.title}
                </span>
                <span className="uppercase tracking-wider text-muted-foreground">
                  {item.source}
                </span>
              </a>
            ))}

            {/* Seamless-loop duplicate: inert spans, not links, so the marquee
                repeats visually without hiding focusable elements from
                assistive tech or announcing every headline twice. */}
            <div className="flex items-center" aria-hidden="true">
              {items.map((item) => (
                <span key={`echo-${item.url}`} className={itemClass}>
                  <span className="text-ui-accent/70">▸</span>
                  <span className="max-w-[34rem] truncate">{item.title}</span>
                  <span className="uppercase tracking-wider text-muted-foreground">
                    {item.source}
                  </span>
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
