"use client"

import { Star } from "lucide-react"
import { cn } from "@/lib/utils"

interface StarRatingProps {
  rating: number
  maxRating?: number
  size?: number
  showValue?: boolean
  className?: string
}

export function StarRating({
  rating,
  maxRating = 5,
  size = 13,
  showValue = false,
  className,
}: StarRatingProps) {
  return (
    <div className={cn("flex items-center gap-0.5", className)}>
      {Array.from({ length: maxRating }, (_, i) => {
        const filled = rating >= i + 1
        const half = !filled && rating >= i + 0.5
        return (
          <span
            key={i}
            className="relative inline-block flex-shrink-0"
            style={{ width: size, height: size }}
          >
            <Star
              size={size}
              className="text-gray-200 absolute inset-0"
              fill="currentColor"
              strokeWidth={0}
            />
            <span
              className="absolute inset-0 overflow-hidden"
              style={{ width: filled ? "100%" : half ? "50%" : "0%" }}
            >
              <Star
                size={size}
                className="text-amber-400 absolute inset-0"
                fill="currentColor"
                strokeWidth={0}
              />
            </span>
          </span>
        )
      })}
      {showValue && (
        <span className="ml-1 text-sm font-semibold text-foreground">{rating.toFixed(1)}</span>
      )}
    </div>
  )
}

interface InteractiveStarRatingProps {
  value: number
  onChange: (value: number) => void
  label?: string
}

export function InteractiveStarRating({ value, onChange, label }: InteractiveStarRatingProps) {
  return (
    <div className="flex items-center gap-1">
      {label && <span className="text-sm text-muted-foreground mr-1">{label}</span>}
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange(value === star ? 0 : star)}
          className="focus:outline-none transition-transform hover:scale-110"
        >
          <Star
            size={18}
            className={star <= value ? "text-amber-400" : "text-gray-200"}
            fill="currentColor"
            strokeWidth={0}
          />
        </button>
      ))}
      {value > 0 && (
        <span className="text-xs text-muted-foreground ml-1">{value}+ stars</span>
      )}
    </div>
  )
}
