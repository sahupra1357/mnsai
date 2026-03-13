export type CourseMode = "online" | "offline" | "hybrid"
export type CourseLevel = "beginner" | "intermediate" | "advanced"
export type CollegeType = "university" | "college" | "institute" | "bootcamp"
export type CostType = "total" | "per-month" | "per-year"
export type SortOption = "distance" | "rating-high" | "price-low" | "price-high" | "relevance"
export type ViewMode = "grid" | "list"

export interface CollegeInfo {
  id: string
  name: string
  type: CollegeType
  location: string
  city: string
  rating: number
  reviewCount: number
  accredited: boolean
  distanceKm: number
}

export interface Course {
  id: string
  title: string
  category: string
  description: string
  highlights: string[]
  rating: number
  reviewCount: number
  cost: number
  costType: CostType
  currency: string
  duration: string
  durationMonths: number
  mode: CourseMode
  level: CourseLevel
  enrollmentOpen: boolean
  nextStartDate: string
  scholarshipAvailable: boolean
  college: CollegeInfo
}

export interface Filters {
  categories: string[]
  modes: CourseMode[]
  levels: CourseLevel[]
  minPrice: string
  maxPrice: string
  minCollegeRating: number
  scholarshipOnly: boolean
}

export const DEFAULT_FILTERS: Filters = {
  categories: [],
  modes: [],
  levels: [],
  minPrice: "",
  maxPrice: "",
  minCollegeRating: 0,
  scholarshipOnly: false,
}
