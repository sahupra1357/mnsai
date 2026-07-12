"use client"

import { useEffect, useState } from "react"
import { rail, sectionOrder } from "@/lib/profile-data"

/**
 * Sticky "On this page" rail (xl+ only, hidden below). IntersectionObserver
 * scrollspy highlights the section currently in view (bold + accent left bar);
 * numbered entries smooth-scroll to their section anchors. Copy is data-driven
 * from `profile-data.ts`. Technique adapted from the frozen v2 draft's
 * section-rail (the draft itself is untouched).
 */
export function PageRail() {
  const [active, setActive] = useState<string>(sectionOrder[0]?.id ?? "")

  useEffect(() => {
    const ids = sectionOrder.map((s) => s.id)
    const els = ids
      .map((id) => document.getElementById(id))
      .filter((el): el is HTMLElement => el !== null)

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible[0]) setActive(visible[0].target.id)
      },
      { rootMargin: "-45% 0px -50% 0px", threshold: 0 }
    )

    els.forEach((el) => observer.observe(el))
    return () => observer.disconnect()
  }, [])

  function onClick(e: React.MouseEvent, id: string) {
    e.preventDefault()
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  return (
    <nav
      aria-label={rail.tocLabel}
      className="sticky top-28 hidden w-48 shrink-0 self-start xl:block"
    >
      <p className="mb-4 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
        {rail.tocLabel}
      </p>
      <ul className="space-y-1 border-l border-border">
        {sectionOrder.map((s) => {
          const isActive = active === s.id
          return (
            <li key={s.id} className="-ml-px">
              <a
                href={`#${s.id}`}
                onClick={(e) => onClick(e, s.id)}
                aria-current={isActive ? "true" : undefined}
                className={`flex items-baseline gap-2.5 border-l-2 py-1.5 pl-4 text-sm transition-colors ${
                  isActive
                    ? "border-ui-accent font-semibold text-foreground"
                    : "border-transparent text-muted-foreground hover:border-border hover:text-foreground"
                }`}
              >
                <span
                  className={`font-mono text-[11px] ${
                    isActive ? "text-ui-accent" : "text-muted-foreground/70"
                  }`}
                >
                  {s.index}
                </span>
                {s.navLabel}
              </a>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
