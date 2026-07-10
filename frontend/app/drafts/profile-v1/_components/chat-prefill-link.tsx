"use client"

import { cn } from "@/lib/utils"

export const CHAT_PREFILL_EVENT = "profile-chat:prefill"

/**
 * Scrolls to the chat section and pre-fills the (stubbed) chat input with a
 * question. The working agent is a later phase; for now this demonstrates the
 * intended flow. Rendered as a styled button so it can be used inside server
 * components (services cards, starter chips) without making them client.
 */
export function ChatPrefillLink({
  question,
  className,
  children,
}: {
  question: string
  className?: string
  children: React.ReactNode
}) {
  function handleClick() {
    if (typeof window !== "undefined") {
      window.dispatchEvent(
        new CustomEvent(CHAT_PREFILL_EVENT, { detail: question })
      )
      document
        .getElementById("chat")
        ?.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }

  return (
    <button type="button" onClick={handleClick} className={cn(className)}>
      {children}
    </button>
  )
}
