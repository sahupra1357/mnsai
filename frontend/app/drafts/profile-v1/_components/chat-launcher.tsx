"use client"

import { useEffect, useState } from "react"
import { MessageCircle } from "lucide-react"

/**
 * Floating chat launcher, bottom-right, visible while scrolling. Scrolls to the
 * embedded chat section. Hidden until the user scrolls past the hero so it
 * doesn't compete with the hero CTA. The chat itself is a stub for now.
 */
export function ChatLauncher() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    function onScroll() {
      setVisible(window.scrollY > 500)
    }
    onScroll()
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  function handleClick() {
    document
      .getElementById("chat")
      ?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-label="Open AI assistant"
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-full bg-ui-main px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-ui-main/25 transition-all duration-300 hover:bg-[#003d8f] hover:shadow-xl ${
        visible
          ? "translate-y-0 opacity-100"
          : "pointer-events-none translate-y-4 opacity-0"
      }`}
    >
      <MessageCircle className="h-5 w-5" />
      <span className="hidden sm:inline">Ask my AI assistant</span>
    </button>
  )
}
