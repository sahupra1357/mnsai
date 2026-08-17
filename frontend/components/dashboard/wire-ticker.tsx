import type { WireItem } from "@/lib/ai-pulse/types"

/**
 * The Wire — the dashboard's signature element, and the first appearance of
 * the instrument material: a trading-desk tape directly under the masthead.
 * Server component; the motion is pure CSS so it costs no JS. Pauses on
 * hover/focus, and prefers-reduced-motion gets a static strip.
 */

/** Shared by the real links and their inert visual echo so both measure the
 *  same width — the -50% loop only lands seamlessly if the halves match. */
const itemClass =
  "group flex shrink-0 items-baseline gap-2.5 px-6 py-2.5 font-mono text-[12px] tracking-tight"

export function WireTicker({ items }: { items: WireItem[] }) {
  if (items.length === 0) return null

  return (
    <div className="wire-ticker instrument relative overflow-hidden">
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
        <div className="z-10 flex shrink-0 items-center gap-2.5 border-r px-5 py-2.5 inst-rule">
          <span
            className="inst-live-dot h-1.5 w-1.5 animate-pulse rounded-full"
            aria-hidden="true"
          />
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.22em] inst-accent">
            AI Wire
          </span>
        </div>

        <div className="relative flex-1 overflow-hidden">
          {/* Fades the tape into the slab at the right edge instead of
              cutting a headline off mid-word against a hard border. */}
          <div
            className="pointer-events-none absolute inset-y-0 right-0 z-10 w-24 bg-gradient-to-l from-[hsl(var(--inst-bg))] to-transparent"
            aria-hidden="true"
          />
          <div className="wire-track flex items-center">
            {/* Real links — the only copy in the a11y tree and tab order. */}
            {items.map((item) => (
              <a
                key={item.url}
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className={`${itemClass} hover:!text-[hsl(var(--inst-accent))] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[hsl(var(--inst-accent))]`}
              >
                <span className="inst-accent opacity-60" aria-hidden="true">
                  ▸
                </span>
                <span className="max-w-[34rem] truncate group-hover:underline">
                  {item.title}
                </span>
                <span className="text-[10px] uppercase tracking-wider inst-dim">
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
                  <span className="inst-accent opacity-60">▸</span>
                  <span className="max-w-[34rem] truncate">{item.title}</span>
                  <span className="text-[10px] uppercase tracking-wider inst-dim">
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
