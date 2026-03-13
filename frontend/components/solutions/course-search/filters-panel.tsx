"use client"

import { RotateCcw, SlidersHorizontal } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from "@/components/ui/sheet"
import { InteractiveStarRating } from "./star-rating"
import { ALL_CATEGORIES } from "./mock-data"
import type { Filters, CourseMode, CourseLevel } from "./types"

interface FiltersPanelProps {
  filters: Filters
  onChange: (filters: Filters) => void
  onReset: () => void
}

const MODES: { value: CourseMode; label: string }[] = [
  { value: "online", label: "Online" },
  { value: "offline", label: "In-person" },
  { value: "hybrid", label: "Hybrid" },
]

const LEVELS: { value: CourseLevel; label: string }[] = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
]

function FiltersContent({ filters, onChange, onReset }: FiltersPanelProps) {
  function toggleArray<T extends string>(arr: T[], value: T): T[] {
    return arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value]
  }

  const activeCount =
    filters.categories.length +
    filters.modes.length +
    filters.levels.length +
    (filters.minPrice ? 1 : 0) +
    (filters.maxPrice ? 1 : 0) +
    (filters.minCollegeRating > 0 ? 1 : 0) +
    (filters.scholarshipOnly ? 1 : 0)

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-sm">Filters</h3>
          {activeCount > 0 && (
            <span className="bg-primary text-primary-foreground text-xs px-1.5 py-0.5 rounded-full font-medium">
              {activeCount}
            </span>
          )}
        </div>
        {activeCount > 0 && (
          <button
            onClick={onReset}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <RotateCcw size={11} />
            Reset
          </button>
        )}
      </div>

      <Separator />

      {/* Category */}
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2.5">
          Category
        </p>
        <div className="space-y-2">
          {ALL_CATEGORIES.map((cat) => (
            <div key={cat} className="flex items-center gap-2">
              <Checkbox
                id={`cat-${cat}`}
                checked={filters.categories.includes(cat)}
                onCheckedChange={() =>
                  onChange({ ...filters, categories: toggleArray(filters.categories, cat) })
                }
              />
              <Label htmlFor={`cat-${cat}`} className="text-sm font-normal cursor-pointer">
                {cat}
              </Label>
            </div>
          ))}
        </div>
      </div>

      <Separator />

      {/* Delivery Mode */}
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2.5">
          Delivery Mode
        </p>
        <div className="space-y-2">
          {MODES.map(({ value, label }) => (
            <div key={value} className="flex items-center gap-2">
              <Checkbox
                id={`mode-${value}`}
                checked={filters.modes.includes(value)}
                onCheckedChange={() =>
                  onChange({ ...filters, modes: toggleArray(filters.modes, value) })
                }
              />
              <Label htmlFor={`mode-${value}`} className="text-sm font-normal cursor-pointer">
                {label}
              </Label>
            </div>
          ))}
        </div>
      </div>

      <Separator />

      {/* Level */}
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2.5">
          Level
        </p>
        <div className="space-y-2">
          {LEVELS.map(({ value, label }) => (
            <div key={value} className="flex items-center gap-2">
              <Checkbox
                id={`level-${value}`}
                checked={filters.levels.includes(value)}
                onCheckedChange={() =>
                  onChange({ ...filters, levels: toggleArray(filters.levels, value) })
                }
              />
              <Label htmlFor={`level-${value}`} className="text-sm font-normal cursor-pointer">
                {label}
              </Label>
            </div>
          ))}
        </div>
      </div>

      <Separator />

      {/* Price Range */}
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2.5">
          Price Range (₹)
        </p>
        <div className="flex items-center gap-2">
          <input
            type="number"
            placeholder="Min"
            value={filters.minPrice}
            onChange={(e) => onChange({ ...filters, minPrice: e.target.value })}
            className="w-full border border-border rounded-md px-2 py-1.5 text-sm bg-background outline-none focus:ring-1 focus:ring-primary/50"
          />
          <span className="text-muted-foreground text-xs flex-shrink-0">–</span>
          <input
            type="number"
            placeholder="Max"
            value={filters.maxPrice}
            onChange={(e) => onChange({ ...filters, maxPrice: e.target.value })}
            className="w-full border border-border rounded-md px-2 py-1.5 text-sm bg-background outline-none focus:ring-1 focus:ring-primary/50"
          />
        </div>
      </div>

      <Separator />

      {/* Min College Rating */}
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2.5">
          Min. College Rating
        </p>
        <InteractiveStarRating
          value={filters.minCollegeRating}
          onChange={(v) => onChange({ ...filters, minCollegeRating: v })}
        />
      </div>

      <Separator />

      {/* Scholarship */}
      <div className="flex items-center gap-2">
        <Checkbox
          id="scholarship"
          checked={filters.scholarshipOnly}
          onCheckedChange={(checked) =>
            onChange({ ...filters, scholarshipOnly: !!checked })
          }
        />
        <Label htmlFor="scholarship" className="text-sm font-normal cursor-pointer">
          Scholarship available
        </Label>
      </div>
    </div>
  )
}

/** Desktop sticky sidebar — renders only on lg+ screens */
export function FiltersSidebar(props: FiltersPanelProps) {
  return (
    <aside className="hidden lg:block w-56 flex-shrink-0 sticky top-4 self-start bg-card border border-border rounded-xl p-4 shadow-sm">
      <FiltersContent {...props} />
    </aside>
  )
}

/** Mobile slide-in Sheet trigger — renders only on < lg screens */
export function FiltersMobileTrigger(props: FiltersPanelProps) {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <SlidersHorizontal size={14} />
          Filters
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-72 overflow-y-auto">
        <div className="pt-6">
          <FiltersContent {...props} />
        </div>
      </SheetContent>
    </Sheet>
  )
}
