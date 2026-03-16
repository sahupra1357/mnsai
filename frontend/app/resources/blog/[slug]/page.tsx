"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import WithSubnavigation from "@/components/common/with-subnavigation"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { CalendarDays, ArrowLeft } from "lucide-react"

interface BlogPost {
  id: string
  title: string
  slug: string
  summary: string | null
  content: string
  tags: string | null
  created_at: string
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

export default function BlogDetailPage() {
  const { slug } = useParams<{ slug: string }>()
  const router = useRouter()
  const [post, setPost] = useState<BlogPost | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL
    fetch(`${apiUrl}/api/v1/blog/posts/${slug}`)
      .then((r) => {
        if (r.status === 404) { setNotFound(true); return null }
        return r.json()
      })
      .then((d) => { if (d) setPost(d) })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false))
  }, [slug])

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <WithSubnavigation />

      <div className="mx-auto max-w-3xl w-full px-6 py-12 flex-1">
        <Button asChild variant="ghost" size="sm" className="mb-8 -ml-2 gap-1.5 text-muted-foreground">
          <Link href="/resources/blog">
            <ArrowLeft className="h-4 w-4" /> Back to Blog
          </Link>
        </Button>

        {loading && (
          <div className="text-center text-muted-foreground text-sm py-16">Loading…</div>
        )}

        {notFound && (
          <div className="text-center py-16">
            <p className="text-lg font-semibold text-foreground">Post not found</p>
            <p className="text-sm text-muted-foreground mt-2">This post may have been removed or the URL is incorrect.</p>
          </div>
        )}

        {post && (
          <article>
            {post.tags && (
              <div className="flex flex-wrap gap-1.5 mb-4">
                {post.tags.split(",").map((t) => (
                  <Badge key={t} variant="secondary" className="text-xs">{t.trim()}</Badge>
                ))}
              </div>
            )}

            <h1 className="text-3xl font-extrabold tracking-tight text-foreground sm:text-4xl leading-tight">
              {post.title}
            </h1>

            {post.summary && (
              <p className="mt-4 text-lg text-muted-foreground leading-relaxed">{post.summary}</p>
            )}

            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-4 mb-10 pb-8 border-b">
              <CalendarDays className="h-3.5 w-3.5" />
              {formatDate(post.created_at)}
            </div>

            <div className="prose prose-sm max-w-none text-foreground leading-relaxed whitespace-pre-wrap">
              {post.content}
            </div>
          </article>
        )}
      </div>

      <footer className="px-6 py-8 border-t text-center text-sm text-muted-foreground">
        &copy; {new Date().getFullYear()} mnsAI. All rights reserved.
      </footer>
    </div>
  )
}
