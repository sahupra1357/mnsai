"use client"

import useAuth from "@/hooks/use-auth"
import { useEffect, useState } from "react"

/**
 * Client island for the hero: time-of-day greeting + auth-aware welcome.
 * Auth resolves client-side, so hold the heading's space while it loads
 * rather than flashing the signed-out copy. Everything else on the dashboard
 * stays a server component.
 */
export function Greeting() {
  const { user, isLoading } = useAuth()
  const [greeting, setGreeting] = useState("")

  useEffect(() => {
    const h = new Date().getHours()
    if (h < 12) setGreeting("Good morning")
    else if (h < 17) setGreeting("Good afternoon")
    else setGreeting("Good evening")
  }, [])

  const name = user?.full_name?.split(" ")[0] || user?.email?.split("@")[0]

  return (
    <div className="max-w-2xl">
      {/* Reserve the eyebrow's line so the h1 doesn't jump once the clock
          resolves on the client. */}
      <p className="mb-3 font-mono text-[11px] font-semibold uppercase tracking-[0.22em] text-ui-accent">
        {greeting || " "}
      </p>

      {isLoading ? (
        <div className="h-[3.5rem] w-[22rem] max-w-full animate-pulse rounded bg-muted sm:h-[4.5rem]" />
      ) : (
        <h1 className="font-display text-[2.75rem] font-bold leading-[1.02] tracking-[-0.035em] text-foreground sm:text-6xl">
          {user ? (
            <>
              Welcome back,
              <br />
              <span className="text-ui-accent">{name}</span>
            </>
          ) : (
            <>
              The AI desk
              <br />
              <span className="text-ui-accent">for your documents</span>
            </>
          )}
        </h1>
      )}

      <p className="mt-5 text-base leading-relaxed text-muted-foreground">
        {user
          ? "Your workspace, with a live read on what's moving in AI. Pick a tool and get started."
          : "Five AI tools for documents, contracts, courses, resumes, and coding-agent logs — alongside a live read on what's moving in AI. Sign in to start using them."}
      </p>
    </div>
  )
}
