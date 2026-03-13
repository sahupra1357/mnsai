"use client"

import { Search, MapPin, Loader2, LocateFixed } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

interface SearchHeroProps {
  query: string
  setQuery: (v: string) => void
  locationName: string
  setLocationName: (v: string) => void
  onSearch: () => void
  isLocating: boolean
  onDetectLocation: () => void
}

export function SearchHero({
  query,
  setQuery,
  locationName,
  setLocationName,
  onSearch,
  isLocating,
  onDetectLocation,
}: SearchHeroProps) {
  return (
    <div
      className="relative overflow-hidden py-14 px-4"
      style={{
        background: "linear-gradient(135deg, #003580 0%, #005092 40%, #00766C 100%)",
      }}
    >
      {/* Background geometric decoration */}
      <div className="absolute inset-0 opacity-10 pointer-events-none">
        <div className="absolute top-0 right-0 w-96 h-96 rounded-full bg-white translate-x-1/2 -translate-y-1/2" />
        <div className="absolute bottom-0 left-0 w-64 h-64 rounded-full bg-white -translate-x-1/3 translate-y-1/3" />
      </div>

      <div className="relative max-w-3xl mx-auto text-center">
        <p className="text-white/70 text-sm font-medium tracking-widest uppercase mb-3">
          mnsAI · Course Discovery
        </p>
        <h1 className="text-3xl md:text-4xl font-bold text-white mb-2 leading-tight">
          Find the Right Course,
          <br />
          <span className="text-teal-200">Near You.</span>
        </h1>
        <p className="text-white/70 text-sm mb-8">
          Compare courses from top colleges — rated, priced, and sorted by distance.
        </p>

        <div className="bg-white rounded-2xl shadow-2xl p-3 flex flex-col sm:flex-row gap-2">
          {/* Course search input */}
          <div className="flex items-center gap-2 flex-1 border border-border rounded-lg px-3 py-2 bg-background focus-within:ring-2 focus-within:ring-primary/30">
            <Search size={16} className="text-muted-foreground flex-shrink-0" />
            <input
              type="text"
              placeholder="Course name, skill, or category…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onSearch()}
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
          </div>

          {/* Location input */}
          <div className="flex items-center gap-2 sm:w-52 border border-border rounded-lg px-3 py-2 bg-background focus-within:ring-2 focus-within:ring-primary/30">
            <MapPin size={16} className="text-muted-foreground flex-shrink-0" />
            <input
              type="text"
              placeholder="Your city…"
              value={locationName}
              onChange={(e) => setLocationName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onSearch()}
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground min-w-0"
            />
            <button
              type="button"
              onClick={onDetectLocation}
              title="Detect my location"
              disabled={isLocating}
              className="text-primary hover:text-primary/80 transition-colors flex-shrink-0"
            >
              {isLocating ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <LocateFixed size={14} />
              )}
            </button>
          </div>

          <Button
            onClick={onSearch}
            className="bg-[#003580] hover:bg-[#002660] text-white px-6 rounded-lg sm:rounded-lg h-auto py-2.5"
          >
            <Search size={15} className="mr-1.5" />
            Search
          </Button>
        </div>

        <p className="text-white/50 text-xs mt-4">
          Try: "Data Science", "Web Development", "MBA", "AI"
        </p>
      </div>
    </div>
  )
}
