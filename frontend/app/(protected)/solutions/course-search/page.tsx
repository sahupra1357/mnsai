"use client"

import { useState, useMemo } from "react"
import { Bookmark } from "lucide-react"
import { SearchHero } from "@/components/solutions/course-search/search-hero"
import { FiltersSidebar, FiltersMobileTrigger } from "@/components/solutions/course-search/filters-panel"
import { SortBar } from "@/components/solutions/course-search/sort-bar"
import { ResultsGrid } from "@/components/solutions/course-search/results-grid"
import { MOCK_COURSES } from "@/components/solutions/course-search/mock-data"
import { DEFAULT_FILTERS } from "@/components/solutions/course-search/types"
import type { Filters, SortOption, ViewMode } from "@/components/solutions/course-search/types"

export default function CourseSearchPage() {
  const [query, setQuery] = useState("")
  const [locationName, setLocationName] = useState("")
  const [isLocating, setIsLocating] = useState(false)
  const [isSearching, setIsSearching] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [activeQuery, setActiveQuery] = useState("")

  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS)
  const [sortBy, setSortBy] = useState<SortOption>("distance")
  const [viewMode, setViewMode] = useState<ViewMode>("grid")
  const [shortlisted, setShortlisted] = useState<Set<string>>(new Set())

  // Detect location via browser geolocation
  function handleDetectLocation() {
    if (!navigator.geolocation) {
      setLocationName("Location unavailable")
      return
    }
    setIsLocating(true)
    navigator.geolocation.getCurrentPosition(
      () => {
        // In a real app, reverse-geocode coordinates here
        setLocationName("Bangalore, Karnataka")
        setIsLocating(false)
      },
      () => {
        setLocationName("")
        setIsLocating(false)
      },
      { timeout: 8000 },
    )
  }

  // Simulate async search (swap for real API call later)
  function handleSearch() {
    setIsSearching(true)
    setActiveQuery(query.trim().toLowerCase())
    setHasSearched(true)
    setTimeout(() => setIsSearching(false), 600)
  }

  // Toggle shortlist
  function toggleShortlist(id: string) {
    setShortlisted((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // Filter + sort
  const results = useMemo(() => {
    if (!hasSearched) return []

    let list = MOCK_COURSES.filter((course) => {
      // Text search across title, category, college name
      if (activeQuery) {
        const hay = `${course.title} ${course.category} ${course.college.name}`.toLowerCase()
        if (!hay.includes(activeQuery)) return false
      }

      // Category filter
      if (filters.categories.length > 0 && !filters.categories.includes(course.category)) {
        return false
      }

      // Mode filter
      if (filters.modes.length > 0 && !filters.modes.includes(course.mode)) {
        return false
      }

      // Level filter
      if (filters.levels.length > 0 && !filters.levels.includes(course.level)) {
        return false
      }

      // Price filter (normalise to total cost for comparison)
      const totalCost =
        course.costType === "per-month"
          ? course.cost * course.durationMonths
          : course.costType === "per-year"
          ? course.cost * Math.ceil(course.durationMonths / 12)
          : course.cost

      if (filters.minPrice && totalCost < Number(filters.minPrice)) return false
      if (filters.maxPrice && totalCost > Number(filters.maxPrice)) return false

      // Min college rating
      if (filters.minCollegeRating > 0 && course.college.rating < filters.minCollegeRating) {
        return false
      }

      // Scholarship filter
      if (filters.scholarshipOnly && !course.scholarshipAvailable) return false

      return true
    })

    // Sort
    list = [...list].sort((a, b) => {
      switch (sortBy) {
        case "distance":
          return a.college.distanceKm - b.college.distanceKm
        case "rating-high":
          return b.rating - a.rating
        case "price-low":
          return a.cost - b.cost
        case "price-high":
          return b.cost - a.cost
        default:
          return 0
      }
    })

    return list
  }, [hasSearched, activeQuery, filters, sortBy])

  return (
    <div className="min-h-screen bg-background">
      {/* Hero */}
      <SearchHero
        query={query}
        setQuery={setQuery}
        locationName={locationName}
        setLocationName={setLocationName}
        onSearch={handleSearch}
        isLocating={isLocating}
        onDetectLocation={handleDetectLocation}
      />

      {/* Body */}
      <div className="max-w-screen-xl mx-auto px-4 py-6">
        {/* Shortlist bar */}
        {shortlisted.size > 0 && (
          <div className="mb-4 flex items-center gap-2 bg-primary/5 border border-primary/20 rounded-lg px-4 py-2.5">
            <Bookmark size={14} className="text-primary" />
            <span className="text-sm font-medium text-primary">
              {shortlisted.size} course{shortlisted.size > 1 ? "s" : ""} shortlisted
            </span>
            <button
              onClick={() => setShortlisted(new Set())}
              className="ml-auto text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              Clear all
            </button>
          </div>
        )}

        {/* Mobile: filter trigger + sort bar in one row */}
        <div className="lg:hidden flex items-center gap-3 mb-4 flex-wrap">
          <FiltersMobileTrigger
            filters={filters}
            onChange={setFilters}
            onReset={() => setFilters(DEFAULT_FILTERS)}
          />
          <div className="flex-1">
            <SortBar
              count={results.length}
              sortBy={sortBy}
              onSortChange={setSortBy}
              viewMode={viewMode}
              onViewModeChange={setViewMode}
            />
          </div>
        </div>

        <div className="flex gap-6 items-start">
          {/* Desktop sticky sidebar */}
          <FiltersSidebar
            filters={filters}
            onChange={setFilters}
            onReset={() => setFilters(DEFAULT_FILTERS)}
          />

          {/* Results column */}
          <div className="flex-1 min-w-0 space-y-4">
            {/* Desktop sort bar */}
            <div className="hidden lg:block">
              <SortBar
                count={results.length}
                sortBy={sortBy}
                onSortChange={setSortBy}
                viewMode={viewMode}
                onViewModeChange={setViewMode}
              />
            </div>

            <ResultsGrid
              courses={results}
              viewMode={viewMode}
              isLoading={isSearching}
              hasSearched={hasSearched}
              shortlisted={shortlisted}
              onToggleShortlist={toggleShortlist}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
