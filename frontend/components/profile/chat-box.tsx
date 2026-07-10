"use client"

import { useEffect, useRef, useState } from "react"
import { Send, Sparkles } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { chatSection } from "@/lib/profile-data"
import { CHAT_PREFILL_EVENT, ChatPrefillLink } from "./chat-prefill-link"

/**
 * Working profile chat agent. Streams a document-grounded reply from the
 * Next.js proxy (`/api/profile-chat`) which fronts the FastAPI endpoint. History
 * is kept in component state only (no server persistence). See the
 * `profile-chat-agent` skill. The agent is public — works logged-out.
 */

interface Msg {
  role: "user" | "assistant"
  content: string
}

/** Cap client-sent history so we stay well under the backend's limits. */
const MAX_HISTORY = 12
const MAX_CHARS = 2000

export function ChatBox() {
  const [value, setValue] = useState("")
  const [messages, setMessages] = useState<Msg[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Pre-fill events from service cards / starter chips.
  useEffect(() => {
    function onPrefill(e: Event) {
      const detail = (e as CustomEvent<string>).detail
      if (typeof detail === "string") setValue(detail)
    }
    window.addEventListener(CHAT_PREFILL_EVENT, onPrefill)
    return () => window.removeEventListener(CHAT_PREFILL_EVENT, onPrefill)
  }, [])

  // Auto-scroll the conversation as it grows.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [messages, isStreaming])

  async function send() {
    const text = value.trim()
    if (!text || isStreaming) return
    if (text.length > MAX_CHARS) {
      toast.error(`Please keep messages under ${MAX_CHARS} characters.`)
      return
    }

    const history = [...messages, { role: "user", content: text } as Msg]
    setMessages(history)
    setValue("")
    setIsStreaming(true)

    // Placeholder assistant bubble we stream tokens into.
    setMessages((m) => [...m, { role: "assistant", content: "" }])

    try {
      const res = await fetch("/api/profile-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history.slice(-MAX_HISTORY) }),
      })

      if (!res.ok || !res.body) {
        const err = await res.json().catch(() => ({ detail: "Chat failed" }))
        throw new Error(err.detail || "Chat failed")
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value: chunk } = await reader.read()
        if (done) break
        buffer += decoder.decode(chunk, { stream: true })

        const events = buffer.split("\n\n")
        buffer = events.pop() ?? ""
        for (const evt of events) {
          const line = evt.trim()
          if (!line.startsWith("data:")) continue
          const payload = JSON.parse(line.slice(5).trim())
          if (typeof payload.delta === "string") {
            appendToLast(payload.delta)
          } else if (typeof payload.replace === "string") {
            setLastContent(payload.replace)
          }
          // payload.done is handled implicitly by the reader finishing.
        }
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Something went wrong."
      toast.error(msg)
      // Drop the empty placeholder if nothing streamed.
      setMessages((m) => {
        const last = m[m.length - 1]
        if (last?.role === "assistant" && last.content === "") {
          return m.slice(0, -1)
        }
        return m
      })
    } finally {
      setIsStreaming(false)
    }
  }

  function appendToLast(delta: string) {
    setMessages((m) => {
      const copy = [...m]
      const last = copy[copy.length - 1]
      if (last?.role === "assistant") {
        copy[copy.length - 1] = { ...last, content: last.content + delta }
      }
      return copy
    })
  }

  function setLastContent(content: string) {
    setMessages((m) => {
      const copy = [...m]
      const last = copy[copy.length - 1]
      if (last?.role === "assistant") {
        copy[copy.length - 1] = { ...last, content }
      }
      return copy
    })
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const showGreeting = messages.length === 0

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-ui-accent/10 text-ui-accent">
            <Sparkles className="h-4 w-4" />
          </span>
          <span className="font-semibold text-foreground">
            {chatSection.panelTitle}
          </span>
        </div>
        <Badge variant="secondary" className="gap-1.5 font-mono text-[11px]">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </span>
          {chatSection.statusLabel}
        </Badge>
      </div>

      {/* Conversation area */}
      <div
        ref={scrollRef}
        className="max-h-[420px] min-h-[220px] space-y-3 overflow-y-auto bg-muted/20 px-5 py-6"
      >
        {showGreeting && (
          <div className="max-w-[85%] rounded-2xl rounded-tl-sm border border-border bg-background px-4 py-3 text-sm text-muted-foreground">
            {chatSection.greeting}
          </div>
        )}

        {messages.map((m, i) =>
          m.role === "user" ? (
            <div
              key={i}
              className="ml-auto max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-tr-sm bg-ui-main px-4 py-3 text-sm text-white"
            >
              {m.content}
            </div>
          ) : (
            <div
              key={i}
              className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-tl-sm border border-border bg-background px-4 py-3 text-sm text-foreground"
            >
              {m.content || (
                <span className="inline-flex gap-1 text-muted-foreground">
                  <span className="animate-pulse">●</span>
                  <span className="animate-pulse [animation-delay:150ms]">●</span>
                  <span className="animate-pulse [animation-delay:300ms]">●</span>
                </span>
              )}
            </div>
          )
        )}
      </div>

      {/* Starter chips */}
      <div className="flex flex-wrap gap-2 px-5 pb-2 pt-4">
        {chatSection.starters.map((s) => (
          <ChatPrefillLink
            key={s}
            question={s}
            className="rounded-full border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:border-ui-accent/40 hover:bg-ui-accent/5 hover:text-ui-accent"
          >
            {s}
          </ChatPrefillLink>
        ))}
      </div>

      {/* Input row */}
      <div className="flex items-end gap-2 p-4">
        <Textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          maxLength={MAX_CHARS}
          placeholder={chatSection.inputPlaceholder}
          className="min-h-[44px] resize-none bg-background"
          aria-label="Chat message"
        />
        <Button
          type="button"
          onClick={send}
          disabled={isStreaming || value.trim().length === 0}
          className="h-11 shrink-0 bg-ui-main text-white hover:bg-[#003d8f]"
          aria-label="Send message"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
      <p className="-mt-2 px-4 pb-4 text-xs text-muted-foreground">
        {chatSection.disabledNote}
      </p>
    </div>
  )
}
