"use client"

import { MapPin, Clock, DollarSign, Bookmark, BookmarkCheck, ExternalLink, Award, GraduationCap, CheckCircle2, CalendarDays } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { StarRating } from "./star-rating"
import type { Course, CourseMode, CourseLevel, CollegeType, ViewMode } from "./types"

// ── Helpers ────────────────────────────────────────────────────────────────

function formatCost(cost: number, costType: string, currency: string): string {
  const symbol = currency === "INR" ? "₹" : "$"
  const formatted = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(cost)
  const suffix = costType === "per-month" ? "/mo" : costType === "per-year" ? "/yr" : " total"
  return `${symbol}${formatted}${suffix}`
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
}

function formatDistance(km: number): string {
  if (km === 0) return "Online"
  return `${km.toFixed(1)} km away`
}

function formatReviews(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k reviews`
  return `${n} reviews`
}

// ── Badge variants ─────────────────────────────────────────────────────────

const MODE_STYLES: Record<CourseMode, string> = {
  online: "bg-emerald-50 text-emerald-700 border-emerald-200",
  offline: "bg-blue-50 text-blue-700 border-blue-200",
  hybrid: "bg-violet-50 text-violet-700 border-violet-200",
}

const MODE_LABELS: Record<CourseMode, string> = {
  online: "Online",
  offline: "In-person",
  hybrid: "Hybrid",
}

const LEVEL_STYLES: Record<CourseLevel, string> = {
  beginner: "bg-sky-50 text-sky-700 border-sky-200",
  intermediate: "bg-orange-50 text-orange-700 border-orange-200",
  advanced: "bg-rose-50 text-rose-700 border-rose-200",
}

const COLLEGE_TYPE_LABELS: Record<CollegeType, string> = {
  university: "University",
  college: "College",
  institute: "Institute",
  bootcamp: "Bootcamp",
}

// ── Card component ─────────────────────────────────────────────────────────

interface CourseCardProps {
  course: Course
  viewMode: ViewMode
  isShortlisted: boolean
  onToggleShortlist: () => void
}

export function CourseCard({ course, viewMode, isShortlisted, onToggleShortlist }: CourseCardProps) {
  if (viewMode === "list") {
    return <CourseCardList course={course} isShortlisted={isShortlisted} onToggleShortlist={onToggleShortlist} />
  }
  return <CourseCardGrid course={course} isShortlisted={isShortlisted} onToggleShortlist={onToggleShortlist} />
}

// ── Grid card ──────────────────────────────────────────────────────────────

function CourseCardGrid({
  course,
  isShortlisted,
  onToggleShortlist,
}: Omit<CourseCardProps, "viewMode">) {
  return (
    <div className="group bg-card border border-border rounded-xl overflow-hidden shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 flex flex-col">
      {/* Top accent bar */}
      <div className="h-1 bg-gradient-to-r from-[#003580] to-[#00766C]" />

      <div className="p-4 flex flex-col gap-3 flex-1">
        {/* College row */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs font-semibold text-[#003580] truncate max-w-[160px]">
                {course.college.name}
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                {COLLEGE_TYPE_LABELS[course.college.type]}
              </span>
              {course.college.accredited && (
                <span title="Accredited">
                  <Award size={11} className="text-amber-500 flex-shrink-0" />
                </span>
              )}
            </div>
            <div className="flex items-center gap-1 mt-0.5">
              <StarRating rating={course.college.rating} size={11} />
              <span className="text-xs text-muted-foreground">
                {course.college.rating.toFixed(1)}
              </span>
              <span className="text-[10px] text-muted-foreground">
                · {formatReviews(course.college.reviewCount)}
              </span>
            </div>
          </div>

          {/* Shortlist button */}
          <button
            onClick={onToggleShortlist}
            title={isShortlisted ? "Remove from shortlist" : "Add to shortlist"}
            className={`flex-shrink-0 p-1 rounded-md transition-colors ${
              isShortlisted
                ? "text-primary bg-primary/10"
                : "text-muted-foreground hover:text-primary hover:bg-primary/10"
            }`}
          >
            {isShortlisted ? <BookmarkCheck size={16} /> : <Bookmark size={16} />}
          </button>
        </div>

        {/* Course title */}
        <div>
          <h3 className="font-semibold text-sm leading-snug line-clamp-2">{course.title}</h3>
          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{course.description}</p>
        </div>

        {/* Course rating */}
        <div className="flex items-center gap-1.5">
          <StarRating rating={course.rating} size={12} />
          <span className="text-xs font-semibold">{course.rating.toFixed(1)}</span>
          <span className="text-xs text-muted-foreground">({formatReviews(course.reviewCount)})</span>
        </div>

        {/* Mode + Level badges */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className={`text-[11px] px-2 py-0.5 rounded-full border font-medium ${MODE_STYLES[course.mode]}`}>
            {MODE_LABELS[course.mode]}
          </span>
          <span className={`text-[11px] px-2 py-0.5 rounded-full border font-medium ${LEVEL_STYLES[course.level]}`}>
            {course.level.charAt(0).toUpperCase() + course.level.slice(1)}
          </span>
          {course.scholarshipAvailable && (
            <span className="text-[11px] px-2 py-0.5 rounded-full border font-medium bg-amber-50 text-amber-700 border-amber-200">
              Scholarship
            </span>
          )}
        </div>

        {/* Highlights */}
        <div className="flex flex-wrap gap-1">
          {course.highlights.map((h) => (
            <span
              key={h}
              className="inline-flex items-center gap-1 text-[11px] bg-muted text-muted-foreground px-2 py-0.5 rounded"
            >
              <CheckCircle2 size={9} className="text-emerald-500" />
              {h}
            </span>
          ))}
        </div>

        <Separator />

        {/* Stats row */}
        <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <DollarSign size={12} className="text-emerald-600 flex-shrink-0" />
            <span className="font-semibold text-foreground">
              {formatCost(course.cost, course.costType, course.currency)}
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <MapPin size={12} className="text-[#003580] flex-shrink-0" />
            <span>{formatDistance(course.college.distanceKm)}</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock size={12} className="flex-shrink-0" />
            <span>{course.duration}</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <CalendarDays size={12} className="flex-shrink-0" />
            <span className={course.enrollmentOpen ? "text-emerald-600 font-medium" : "text-muted-foreground"}>
              {course.enrollmentOpen ? `Starts ${formatDate(course.nextStartDate)}` : "Enrollment closed"}
            </span>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 pb-4 pt-0">
        <Button
          size="sm"
          className="w-full bg-[#003580] hover:bg-[#002660] text-white gap-1.5 text-xs"
        >
          <ExternalLink size={12} />
          View Details
        </Button>
      </div>
    </div>
  )
}

// ── List card ──────────────────────────────────────────────────────────────

function CourseCardList({
  course,
  isShortlisted,
  onToggleShortlist,
}: Omit<CourseCardProps, "viewMode">) {
  return (
    <div className="group bg-card border border-border rounded-xl shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden">
      <div className="flex gap-0">
        {/* Left accent stripe */}
        <div className="w-1 flex-shrink-0 bg-gradient-to-b from-[#003580] to-[#00766C]" />

        <div className="flex flex-col sm:flex-row gap-4 p-4 flex-1 min-w-0">
          {/* Main content */}
          <div className="flex-1 min-w-0 space-y-2">
            {/* College */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <GraduationCap size={13} className="text-[#003580] flex-shrink-0" />
              <span className="text-xs font-semibold text-[#003580]">{course.college.name}</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                {COLLEGE_TYPE_LABELS[course.college.type]}
              </span>
              {course.college.accredited && (
                <span title="Accredited">
                  <Award size={11} className="text-amber-500" />
                </span>
              )}
              <div className="flex items-center gap-1 ml-1">
                <StarRating rating={course.college.rating} size={11} />
                <span className="text-xs text-muted-foreground">{course.college.rating.toFixed(1)}</span>
              </div>
            </div>

            {/* Title + description */}
            <div>
              <h3 className="font-semibold text-sm leading-snug">{course.title}</h3>
              <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{course.description}</p>
            </div>

            {/* Badges row */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <div className="flex items-center gap-1">
                <StarRating rating={course.rating} size={11} />
                <span className="text-xs font-semibold">{course.rating.toFixed(1)}</span>
                <span className="text-xs text-muted-foreground">({formatReviews(course.reviewCount)})</span>
              </div>
              <span className="text-muted-foreground">·</span>
              <span className={`text-[11px] px-2 py-0.5 rounded-full border font-medium ${MODE_STYLES[course.mode]}`}>
                {MODE_LABELS[course.mode]}
              </span>
              <span className={`text-[11px] px-2 py-0.5 rounded-full border font-medium ${LEVEL_STYLES[course.level]}`}>
                {course.level.charAt(0).toUpperCase() + course.level.slice(1)}
              </span>
              {course.scholarshipAvailable && (
                <span className="text-[11px] px-2 py-0.5 rounded-full border font-medium bg-amber-50 text-amber-700 border-amber-200">
                  Scholarship
                </span>
              )}
            </div>

            {/* Highlights */}
            <div className="flex flex-wrap gap-1">
              {course.highlights.map((h) => (
                <span
                  key={h}
                  className="inline-flex items-center gap-1 text-[11px] bg-muted text-muted-foreground px-2 py-0.5 rounded"
                >
                  <CheckCircle2 size={9} className="text-emerald-500" />
                  {h}
                </span>
              ))}
            </div>
          </div>

          {/* Right: stats + actions */}
          <div className="sm:w-44 flex-shrink-0 flex flex-col justify-between gap-3">
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5 text-sm">
                <DollarSign size={13} className="text-emerald-600 flex-shrink-0" />
                <span className="font-bold text-foreground">
                  {formatCost(course.cost, course.costType, course.currency)}
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <MapPin size={12} className="text-[#003580] flex-shrink-0" />
                <span>{formatDistance(course.college.distanceKm)}</span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Clock size={12} className="flex-shrink-0" />
                <span>{course.duration}</span>
              </div>
              <div className="flex items-center gap-1.5 text-xs">
                <CalendarDays size={12} className="flex-shrink-0 text-muted-foreground" />
                <span className={course.enrollmentOpen ? "text-emerald-600 font-medium" : "text-muted-foreground"}>
                  {course.enrollmentOpen ? formatDate(course.nextStartDate) : "Closed"}
                </span>
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                size="sm"
                className="flex-1 bg-[#003580] hover:bg-[#002660] text-white text-xs gap-1"
              >
                <ExternalLink size={11} />
                Details
              </Button>
              <button
                onClick={onToggleShortlist}
                title={isShortlisted ? "Remove from shortlist" : "Shortlist"}
                className={`p-1.5 rounded-md border transition-colors ${
                  isShortlisted
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border text-muted-foreground hover:text-primary hover:border-primary hover:bg-primary/10"
                }`}
              >
                {isShortlisted ? <BookmarkCheck size={14} /> : <Bookmark size={14} />}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
