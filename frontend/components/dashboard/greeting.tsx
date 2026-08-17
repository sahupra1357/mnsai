"use client"

import useAuth from "@/hooks/use-auth"
import { useEffect, useState } from "react"

/**
 * Client island for the header band: time-of-day greeting + auth-aware
 * welcome. Auth resolves client-side, so hold the heading's space while it
 * loads rather than flashing the signed-out copy. Everything else on the
 * dashboard stays a server component.
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
    <div>
      <p className="mb-1 font-mono text-[11px] font-medium uppercase tracking-[0.2em] text-ui-accent">
        {greeting || " "}
      </p>
      {isLoading ? (
        <div className="h-9 w-72 max-w-full animate-pulse rounded bg-muted" />
      ) : (
        <h1 className="font-display text-3xl font-bold tracking-tight text-foreground">
          {user ? `Welcome back, ${name}` : "Welcome to mnsAI"}
        </h1>
      )}
      <p className="mt-2 max-w-2xl text-muted-foreground">
        {user
          ? "Here's your mnsAI workspace. Pick a tool and get started."
          : "AI tools for documents, contracts, courses, and resumes — with a live view of what's moving in AI. Sign in to start using the tools."}
      </p>
    </div>
  )
}
