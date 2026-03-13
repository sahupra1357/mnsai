"use client"

import { BookOpen, Search } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"
import { CourseCard } from "./course-card"
import type { Course, ViewMode } from "./types"

interface ResultsGridProps {
  courses: Course[]
  viewMode: ViewMode
  isLoading: boolean
  hasSearched: boolean
  shortlisted: Set<string>
  onToggleShortlist: (id: string) => void
}

function SkeletonCard({ viewMode }: { viewMode: ViewMode }) {
  if (viewMode === "list") {
    return (
      <div className="bg-card border border-border rounded-xl p-4 flex gap-4">
        <div className="flex-1 space-y-2">
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-4 w-64" />
          <Skeleton className="h-3 w-48" />
          <div className="flex gap-1.5">
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-20 rounded-full" />
          </div>
        </div>
        <div className="w-36 space-y-2">
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-8 w-full mt-4" />
        </div>
      </div>
    )
  }
  return (
    <div className="bg-card border border-border rounded-xl p-4 space-y-3">
      <Skeleton className="h-3 w-28" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-3 w-48" />
      <div className="flex gap-1.5">
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-5 w-20 rounded-full" />
      </div>
      <div className="pt-2 grid grid-cols-2 gap-2">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-3 w-16" />
      </div>
      <Skeleton className="h-8 w-full mt-1" />
    </div>
  )
}

export function ResultsGrid({
  courses,
  viewMode,
  isLoading,
  hasSearched,
  shortlisted,
  onToggleShortlist,
}: ResultsGridProps) {
  // Loading state
  if (isLoading) {
    return (
      <div
        className={
          viewMode === "grid"
            ? "grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4"
            : "flex flex-col gap-3"
        }
      >
        {Array.from({ length: 6 }, (_, i) => (
          <SkeletonCard key={i} viewMode={viewMode} />
        ))}
      </div>
    )
  }

  // No search yet
  if (!hasSearched) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
          <Search size={28} className="text-primary" />
        </div>
        <h3 className="font-semibold text-lg mb-1">Search for a course</h3>
        <p className="text-muted-foreground text-sm max-w-xs">
          Enter a course name, skill, or category above to find programmes near you.
        </p>
      </div>
    )
  }

  // Empty results
  if (courses.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center mb-4">
          <BookOpen size={28} className="text-muted-foreground" />
        </div>
        <h3 className="font-semibold text-lg mb-1">No courses found</h3>
        <p className="text-muted-foreground text-sm max-w-xs">
          Try a different search term or adjust your filters.
        </p>
      </div>
    )
  }

  return (
    <div
      className={
        viewMode === "grid"
          ? "grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4"
          : "flex flex-col gap-3"
      }
    >
      {courses.map((course) => (
        <CourseCard
          key={course.id}
          course={course}
          viewMode={viewMode}
          isShortlisted={shortlisted.has(course.id)}
          onToggleShortlist={() => onToggleShortlist(course.id)}
        />
      ))}
    </div>
  )
}
