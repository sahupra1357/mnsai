"use client"

import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"
import { useEffect, useState } from "react"
import { cn } from "@/lib/utils"

/**
 * Light/dark switch for the site header. The theme is only known on the
 * client, so until mount it renders a same-sized placeholder rather than
 * guessing an icon and causing a hydration mismatch.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const { resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  const isDark = resolvedTheme === "dark"
  const label = isDark ? "Switch to light mode" : "Switch to dark mode"

  return (
    <button
      type="button"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label={mounted ? label : "Toggle theme"}
      title={mounted ? label : undefined}
      className={cn(
        "inline-flex h-9 w-9 items-center justify-center rounded-full text-foreground/85 transition-colors hover:bg-white/10 hover:text-ui-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-ui-accent",
        className,
      )}
    >
      {mounted ? (
        isDark ? (
          <Sun size={18} />
        ) : (
          <Moon size={18} />
        )
      ) : (
        <span className="h-[18px] w-[18px]" />
      )}
    </button>
  )
}
