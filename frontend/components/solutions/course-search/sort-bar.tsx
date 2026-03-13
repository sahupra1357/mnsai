"use client"

import { LayoutGrid, List } from "lucide-react"
import type { SortOption, ViewMode } from "./types"

interface SortBarProps {
  count: number
  sortBy: SortOption
  onSortChange: (v: SortOption) => void
  viewMode: ViewMode
  onViewModeChange: (v: ViewMode) => void
}

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "distance", label: "Nearest First" },
  { value: "rating-high", label: "Highest Rated" },
  { value: "price-low", label: "Price: Low to High" },
  { value: "price-high", label: "Price: High to Low" },
  { value: "relevance", label: "Most Relevant" },
]

export function SortBar({ count, sortBy, onSortChange, viewMode, onViewModeChange }: SortBarProps) {
  return (
    <div className="flex items-center justify-between gap-3 flex-wrap">
      <p className="text-sm text-muted-foreground">
        <span className="font-semibold text-foreground">{count}</span>{" "}
        {count === 1 ? "course" : "courses"} found
      </p>

      <div className="flex items-center gap-3">
        {/* Sort select */}
        <div className="relative">
          <select
            value={sortBy}
            onChange={(e) => onSortChange(e.target.value as SortOption)}
            className="appearance-none text-sm border border-border rounded-lg px-3 py-1.5 pr-8 bg-background text-foreground outline-none focus:ring-2 focus:ring-primary/30 cursor-pointer"
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground">
            ▾
          </span>
        </div>

        {/* View toggle */}
        <div className="flex items-center border border-border rounded-lg overflow-hidden">
          <button
            onClick={() => onViewModeChange("grid")}
            className={`p-1.5 transition-colors ${
              viewMode === "grid"
                ? "bg-primary text-primary-foreground"
                : "bg-background text-muted-foreground hover:bg-muted"
            }`}
            title="Grid view"
          >
            <LayoutGrid size={15} />
          </button>
          <button
            onClick={() => onViewModeChange("list")}
            className={`p-1.5 transition-colors ${
              viewMode === "list"
                ? "bg-primary text-primary-foreground"
                : "bg-background text-muted-foreground hover:bg-muted"
            }`}
            title="List view"
          >
            <List size={15} />
          </button>
        </div>
      </div>
    </div>
  )
}
