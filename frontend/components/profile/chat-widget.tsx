"use client"

import { useEffect, useRef, useState } from "react"
import { MessageCircle, Send, X } from "lucide-react"
import { toast } from "sonner"
import { chatWidget } from "@/lib/profile-data"
import { CHAT_PREFILL_EVENT } from "./chat-prefill-link"

/**
 * Floating chat widget — the ONLY chat surface on the page. A bottom-right
 * circular launcher toggles a messenger-style popover panel (full-screen sheet
 * on mobile). Streams a document-grounded reply from the Next.js proxy
 * (`/api/profile-chat`) which fronts the FastAPI endpoint; history lives in
 * component state only. Public — works logged-out. See the profile-chat-agent
 * skill. The OpenAI key may be invalid in dev, so a failed stream surfaces a
 * graceful error toast rather than crashing.
 */

interface Msg {
  role: "user" | "assistant"
  content: string
}

/** Cap client-sent history so we stay well under the backend's limits. */
const MAX_HISTORY = 12
const MAX_CHARS = 2000

export function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [value, setValue] = useState("")
  const [messages, setMessages] = useState<Msg[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const launcherRef = useRef<HTMLButtonElement>(null)

  // Prefill / open events from external CTAs (e.g. the platform project panel).
  useEffect(() => {
    function onPrefill(e: Event) {
      const detail = (e as CustomEvent<string>).detail
      setOpen(true)
      if (typeof detail === "string" && detail.length > 0) {
        setValue(detail)
        // Focus the input after the panel has painted.
        requestAnimationFrame(() => inputRef.current?.focus())
      }
    }
    window.addEventListener(CHAT_PREFILL_EVENT, onPrefill)
    return () => window.removeEventListener(CHAT_PREFILL_EVENT, onPrefill)
  }, [])

  // Auto-scroll the conversation as it grows / on open.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [messages, isStreaming, open])

  // Close on Escape while the panel is open.
  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open])

  // Close when clicking anywhere outside the panel. Two exclusions: the
  // launcher, whose own toggle stays authoritative (otherwise it would close
  // here and immediately reopen on click), and sonner's toast portal, so
  // dismissing a chat error doesn't take the conversation with it. Messages
  // survive closing, so reopening resumes where the visitor left off.
  useEffect(() => {
    if (!open) return
    function onPointerDown(e: PointerEvent) {
      const target = e.target as Node | null
      if (!target) return
      if (panelRef.current?.contains(target)) return
      if (launcherRef.current?.contains(target)) return
      const el =
        target instanceof Element ? target : (target.parentElement ?? null)
      if (el?.closest("[data-sonner-toaster]")) return
      setOpen(false)
    }
    document.addEventListener("pointerdown", onPointerDown)
    return () => document.removeEventListener("pointerdown", onPointerDown)
  }, [open])

  function prefill(question: string) {
    setValue(question)
    inputRef.current?.focus()
  }

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

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const showGreeting = messages.length === 0

  return (
    <>
      {/* Popover panel */}
      {open && (
        <div
          ref={panelRef}
          role="dialog"
          aria-label={chatWidget.name}
          className="fixed inset-0 z-50 flex flex-col overflow-hidden border-border bg-card shadow-2xl sm:inset-auto sm:bottom-24 sm:right-6 sm:h-[560px] sm:max-h-[calc(100vh-8rem)] sm:w-[380px] sm:rounded-2xl sm:border"
        >
          {/* Header */}
          <div className="flex items-center gap-3 border-b border-border bg-gradient-to-br from-ui-main to-[#0e7490] px-4 py-3.5 text-white">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/15 ring-2 ring-white/30">
              <span className="font-display text-sm font-bold tracking-tight">
                PS
              </span>
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold leading-tight">
                {chatWidget.name}
              </p>
              <p className="flex items-center gap-1.5 text-xs text-teal-50/85">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-300 opacity-75" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
                </span>
                {chatWidget.tagline}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label={chatWidget.launcherCloseLabel}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white/80 transition-colors hover:bg-white/15 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Conversation area */}
          <div
            ref={scrollRef}
            className="flex-1 space-y-3 overflow-y-auto bg-muted/20 px-4 py-4"
          >
            {showGreeting && (
              <div className="max-w-[85%] rounded-2xl rounded-tl-sm border border-border bg-background px-4 py-3 text-sm text-muted-foreground">
                {chatWidget.greeting}
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
                      <span className="animate-pulse [animation-delay:150ms]">
                        ●
                      </span>
                      <span className="animate-pulse [animation-delay:300ms]">
                        ●
                      </span>
                    </span>
                  )}
                </div>
              )
            )}
          </div>

          {/* Starter chips */}
          {showGreeting && (
            <div className="flex flex-wrap gap-2 border-t border-border bg-card px-4 pb-1 pt-3">
              {chatWidget.starters.map((s) => {
                const Icon = s.icon
                return (
                  <button
                    key={s.label}
                    type="button"
                    onClick={() => prefill(s.question)}
                    className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:border-ui-accent/40 hover:bg-ui-accent/5 hover:text-ui-accent"
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {s.label}
                  </button>
                )
              })}
            </div>
          )}

          {/* Input bar */}
          <div className="border-t border-border bg-card px-3 py-3">
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={onKeyDown}
                maxLength={MAX_CHARS}
                placeholder={chatWidget.inputPlaceholder}
                aria-label="Chat message"
                className="h-10 min-w-0 flex-1 rounded-full border border-border bg-background px-4 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-ui-accent/50"
              />
              <button
                type="button"
                onClick={send}
                disabled={isStreaming || value.trim().length === 0}
                aria-label={chatWidget.sendLabel}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-ui-main text-white transition-colors hover:bg-[#0b5c56] disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
            <p className="mt-2 px-1 text-[11px] leading-snug text-muted-foreground">
              {chatWidget.disclaimer}
            </p>
          </div>
        </div>
      )}

      {/* Launcher */}
      <button
        ref={launcherRef}
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? chatWidget.launcherCloseLabel : chatWidget.launcherOpenLabel}
        aria-expanded={open}
        className={`fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-ui-main to-[#0e7490] text-white shadow-lg shadow-ui-main/30 transition-all duration-200 hover:shadow-xl hover:brightness-110 ${
          open ? "max-sm:hidden" : ""
        }`}
      >
        {open ? (
          <X className="h-6 w-6" />
        ) : (
          <MessageCircle className="h-6 w-6" />
        )}
      </button>
    </>
  )
}
