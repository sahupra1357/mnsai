"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import WithSubnavigation from "@/components/common/with-subnavigation"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { CalendarDays, ArrowRight } from "lucide-react"

interface BlogPost {
  id: string
  title: string
  slug: string
  summary: string | null
  tags: string | null
  created_at: string
  is_published: boolean
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

export default function BlogListPage() {
  const [posts, setPosts] = useState<BlogPost[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL
    fetch(`${apiUrl}/api/v1/blog/posts`)
      .then((r) => r.json())
      .then((d) => setPosts(d.data ?? []))
      .catch(() => setPosts([]))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <WithSubnavigation />

      {/* Hero */}
      <section className="border-b bg-muted/30 px-6 py-16 text-center">
        <span className="inline-flex items-center gap-2 rounded-full border border-ui-main/20 bg-ui-main/5 px-4 py-1.5 text-xs font-semibold text-ui-main uppercase tracking-widest mb-4">
          Blog
        </span>
        <h1 className="text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl">
          Insights & Updates
        </h1>
        <p className="mt-3 text-muted-foreground max-w-xl mx-auto">
          Thoughts on AI, product updates, tutorials, and everything in between.
        </p>
      </section>

      {/* Posts */}
      <section className="px-6 py-14">
        <div className="mx-auto max-w-3xl space-y-6">
          {loading && (
            <div className="text-center text-muted-foreground text-sm py-16">Loading posts…</div>
          )}

          {!loading && posts.length === 0 && (
            <div className="text-center text-muted-foreground text-sm py-16">
              No posts published yet. Check back soon.
            </div>
          )}

          {posts.map((post) => (
            <Link key={post.id} href={`/resources/blog/${post.slug}`} className="group block">
              <Card className="hover:shadow-md transition-shadow duration-200 border border-border">
                <CardContent className="pt-6 pb-6 flex flex-col gap-3">
                  {post.tags && (
                    <div className="flex flex-wrap gap-1.5">
                      {post.tags.split(",").map((t) => (
                        <Badge key={t} variant="secondary" className="text-xs">
                          {t.trim()}
                        </Badge>
                      ))}
                    </div>
                  )}
                  <h2 className="text-xl font-bold text-foreground group-hover:text-ui-main transition-colors">
                    {post.title}
                  </h2>
                  {post.summary && (
                    <p className="text-sm text-muted-foreground leading-relaxed">{post.summary}</p>
                  )}
                  <div className="flex items-center justify-between mt-1">
                    <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <CalendarDays className="h-3.5 w-3.5" />
                      {formatDate(post.created_at)}
                    </span>
                    <span className="flex items-center gap-1 text-xs font-semibold text-ui-main group-hover:underline">
                      Read more <ArrowRight className="h-3 w-3" />
                    </span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      <footer className="mt-auto px-6 py-8 border-t text-center text-sm text-muted-foreground">
        &copy; {new Date().getFullYear()} mnsAI. All rights reserved.
      </footer>
    </div>
  )
}
