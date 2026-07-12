"use client"

import { useEffect, useState } from "react"
import { rail, sectionOrder } from "./profile-data"

/**
 * Slim sticky table-of-contents rail (xl+ only). Uses IntersectionObserver
 * scrollspy to highlight the section in view and pins an "Ask my AI assistant"
 * CTA. Hidden below xl — the reading column stands on its own on small screens.
 */
export function SectionRail() {
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

  return (
    <nav
      aria-label={rail.tocLabel}
      className="sticky top-24 hidden w-52 shrink-0 xl:block"
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

      <a
        href="#chat"
        className="mt-6 block rounded-md bg-ui-main px-4 py-2.5 text-center text-sm font-semibold text-white transition-colors hover:bg-[#003d8f]"
      >
        {rail.ctaLabel}
      </a>
    </nav>
  )
}
