import { cn } from "@/lib/utils"

/**
 * mnsAI brand mark: the terminal-prompt tile plus the ">mnsAI▌" wordmark.
 * Drawn in markup rather than shipped as the PNG (public/assets/images/mnsai_3.png)
 * so it is theme-aware — the "mns" letters and the cursor take the foreground
 * colour, and the lime accents use ui-accent, which is darkened in light mode
 * to stay legible on paper. The tile keeps the logo's own ink-and-lime colours
 * in both themes.
 */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 64 64"
      aria-hidden="true"
      className={cn("h-8 w-8 shrink-0", className)}
    >
      <rect
        x="3"
        y="3"
        width="58"
        height="58"
        rx="14"
        fill="#161616"
        stroke="#a6e22e"
        strokeWidth="4"
      />
      <path
        d="M20 22 L32 31 L20 40"
        fill="none"
        stroke="#a6e22e"
        strokeWidth="5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <rect x="34" y="40" width="13" height="4.5" rx="1" fill="#f2f2f2" />
    </svg>
  )
}

export function Logo({
  className,
  size = "md",
}: {
  className?: string
  size?: "md" | "lg"
}) {
  return (
    <span
      role="img"
      aria-label="mnsAI logo"
      className={cn(
        "inline-flex items-center font-mono font-bold leading-none tracking-tight",
        size === "lg" ? "gap-3 text-3xl" : "gap-2.5 text-xl",
        className,
      )}
    >
      <LogoMark className={size === "lg" ? "h-11 w-11" : undefined} />
      <span className="inline-flex items-center">
        <span className="text-ui-accent">&gt;</span>
        <span className="text-foreground">mns</span>
        <span className="text-ui-accent">AI</span>
        <span
          className={cn(
            "ml-1 inline-block bg-foreground",
            size === "lg" ? "h-8 w-3.5" : "h-5 w-2.5",
          )}
        />
      </span>
    </span>
  )
}
