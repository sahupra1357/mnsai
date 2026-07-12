import { Plus } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * Dashed-border blank slot for a structural section that has no approved content
 * yet (employers, testimonials, press logos, social posts). Driven by an empty
 * array / null in profile-data — filling it later is a data change, not code.
 */
export function PlaceholderCard({
  label,
  className,
}: {
  label: string
  className?: string
}) {
  return (
    <div
      className={cn(
        "flex min-h-[120px] flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border/80 bg-muted/20 px-6 py-8 text-center",
        className
      )}
    >
      <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-dashed border-border text-muted-foreground/70">
        <Plus className="h-4 w-4" />
      </span>
      <span className="text-sm font-medium text-muted-foreground/80">
        {label}
      </span>
    </div>
  )
}
