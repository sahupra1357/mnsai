import Link from "next/link"
import { ArrowUpRight } from "lucide-react"
import { socialPosts, sharing } from "@/lib/profile-data"
import { PlaceholderCard } from "./placeholder-card"

/**
 * Sharing / social proof. No approved posts or talks yet → `socialPosts` is
 * empty, so the section renders `sharing.placeholderCount` blank dashed cards.
 * Adding real posts later is a data change only.
 */
export function Sharing() {
  if (socialPosts.length === 0) {
    return (
      <div className="grid gap-5 sm:grid-cols-2">
        {Array.from({ length: sharing.placeholderCount }).map((_, i) => (
          <PlaceholderCard key={i} label={sharing.placeholder} />
        ))}
      </div>
    )
  }

  return (
    <div className="grid gap-5 sm:grid-cols-2">
      {socialPosts.map((post) => (
        <Link
          key={post.title}
          href={post.href}
          className="group flex flex-col rounded-2xl border border-border bg-card p-6 shadow-sm transition-all hover:border-ui-accent/40 hover:shadow-md"
        >
          <p className="flex-1 text-sm leading-relaxed text-foreground">
            {post.title}
          </p>
          <span className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-ui-accent">
            {post.source}
            <ArrowUpRight className="h-4 w-4" />
          </span>
        </Link>
      ))}
    </div>
  )
}
