"use client"

import { useEffect, useState } from "react"
import { Send, Sparkles, Lock } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { chatSection } from "./profile-data"
import { CHAT_PREFILL_EVENT, ChatPrefillLink } from "./chat-prefill-link"

/**
 * UI stub for the profile chat agent. Renders the panel + input in a disabled
 * "coming soon" state. The document-grounded (RAG) backend and streaming are a
 * later phase — see the `profile-chat-agent` skill. Do not wire a backend here.
 */
export function ChatBox() {
  const [value, setValue] = useState("")

  useEffect(() => {
    function onPrefill(e: Event) {
      const detail = (e as CustomEvent<string>).detail
      if (typeof detail === "string") setValue(detail)
    }
    window.addEventListener(CHAT_PREFILL_EVENT, onPrefill)
    return () => window.removeEventListener(CHAT_PREFILL_EVENT, onPrefill)
  }, [])

  return (
    <div className="mx-auto max-w-3xl">
      <div className="rounded-2xl border border-border bg-background shadow-sm overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-ui-main/10 text-ui-main">
              <Sparkles className="h-4 w-4" />
            </span>
            <span className="font-semibold text-foreground">AI Assistant</span>
          </div>
          <Badge variant="secondary" className="gap-1">
            <Lock className="h-3 w-3" /> Coming soon
          </Badge>
        </div>

        {/* Conversation preview area */}
        <div className="px-5 py-6 min-h-[180px] bg-muted/20">
          <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-background border border-border px-4 py-3 text-sm text-muted-foreground">
            Hi! I&apos;m Pradeep&apos;s AI assistant. Soon I&apos;ll answer your
            questions about his skills, projects, and services — grounded in his
            actual resume and project docs. The assistant is being wired up now.
          </div>
        </div>

        {/* Starter chips */}
        <div className="flex flex-wrap gap-2 px-5 pb-2">
          {chatSection.starters.map((s) => (
            <ChatPrefillLink
              key={s}
              question={s}
              className="rounded-full border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:border-ui-main/40 hover:bg-ui-main/5 hover:text-ui-main"
            >
              {s}
            </ChatPrefillLink>
          ))}
        </div>

        {/* Input row (disabled stub) */}
        <div className="flex items-end gap-2 p-4">
          <Textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            disabled
            rows={1}
            placeholder="Ask about my experience, projects, or services…"
            className="min-h-[44px] resize-none bg-muted/30"
            aria-label="Chat message (coming soon)"
          />
          <Button
            type="button"
            disabled
            className="h-11 shrink-0 bg-ui-main text-white hover:bg-[#003d8f]"
            aria-label="Send (coming soon)"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <p className="px-4 pb-4 -mt-2 text-xs text-muted-foreground">
          Chat is coming soon. In the meantime, reach me directly from the
          section below.
        </p>
      </div>
    </div>
  )
}
