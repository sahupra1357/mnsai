"use client"

import { cn } from "@/lib/utils"
import { ArrowRight } from "lucide-react"

/**
 * Event the floating chat widget listens for. Dispatching it opens the widget;
 * a non-empty `detail` string is prefilled into the input. There is no in-page
 * chat section anymore — everything routes through the widget.
 */
export const CHAT_PREFILL_EVENT = "profile-chat:prefill"

/** Open the widget and (optionally) prefill a question. */
export function openChat(question?: string) {
  if (typeof window === "undefined") return
  window.dispatchEvent(
    new CustomEvent(CHAT_PREFILL_EVENT, { detail: question ?? "" }),
  )
}

/**
 * Styled text CTA (accent + arrow) that opens the floating chat widget. Used by
 * the platform project panel in place of the old `#chat` deep link. A client
 * component so it can live inside server components.
 */
export function ChatOpenLink({
  question,
  className,
  children,
}: {
  question?: string
  className?: string
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={() => openChat(question)}
      className={cn(
        "group inline-flex items-center gap-2 text-sm font-semibold text-ui-accent transition-colors hover:text-ui-main",
        className,
      )}
    >
      {children}
      <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
    </button>
  )
}
