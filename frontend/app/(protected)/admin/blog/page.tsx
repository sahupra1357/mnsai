"use client"

import { useEffect, useState } from "react"
import { useForm, type SubmitHandler } from "react-hook-form"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import useAuth from "@/hooks/use-auth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Switch } from "@/components/ui/switch"
import { Pencil, Trash2, Plus, Eye, Code2 } from "lucide-react"
import { toast } from "sonner"

interface BlogPost {
  id: string
  title: string
  slug: string
  summary: string | null
  content: string
  tags: string | null
  is_published: boolean
  created_at: string
  updated_at: string
}

interface PostForm {
  title: string
  slug: string
  summary: string
  content: string
  tags: string
  is_published: boolean
}

function slugify(title: string) {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "")
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export default function AdminBlogPage() {
  const { user } = useAuth()
  const [posts, setPosts] = useState<BlogPost[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<BlogPost | null>(null)
  const [saving, setSaving] = useState(false)
  const [contentTab, setContentTab] = useState<"write" | "preview">("write")

  const apiUrl = "/api/proxy"

  const { register, handleSubmit, reset, setValue, watch, formState: { errors } } = useForm<PostForm>({
    defaultValues: { is_published: false },
  })

  const titleValue = watch("title")
  const contentValue = watch("content")

  // Auto-generate slug from title when creating new
  useEffect(() => {
    if (!editing && titleValue) {
      setValue("slug", slugify(titleValue))
    }
  }, [titleValue, editing, setValue])

  function loadPosts() {
    fetch(`${apiUrl}/api/v1/blog/posts/all`, { credentials: "include" })
      .then((r) => r.json())
      .then((d) => setPosts(d.data ?? []))
      .catch(() => setPosts([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadPosts() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function openCreate() {
    setEditing(null)
    setContentTab("write")
    reset({ title: "", slug: "", summary: "", content: "", tags: "", is_published: false })
    setOpen(true)
  }

  function openEdit(post: BlogPost) {
    setEditing(post)
    setContentTab("write")
    reset({
      title: post.title,
      slug: post.slug,
      summary: post.summary ?? "",
      content: post.content,
      tags: post.tags ?? "",
      is_published: post.is_published,
    })
    setOpen(true)
  }

  const onSubmit: SubmitHandler<PostForm> = async (data) => {
    setSaving(true)
    try {
      const payload = {
        ...data,
        summary: data.summary || null,
        tags: data.tags || null,
      }
      const url = editing
        ? `${apiUrl}/api/v1/blog/posts/${editing.slug}`
        : `${apiUrl}/api/v1/blog/posts`
      const res = await fetch(url, {
        method: editing ? "PUT" : "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const err = await res.json()
        toast.error(err.detail ?? "Failed to save post")
        return
      }
      toast.success(editing ? "Post updated" : "Post created")
      setOpen(false)
      loadPosts()
    } finally {
      setSaving(false)
    }
  }

  async function deletePost(post: BlogPost) {
    if (!confirm(`Delete "${post.title}"?`)) return
    const res = await fetch(`${apiUrl}/api/v1/blog/posts/${post.slug}`, {
      method: "DELETE",
      credentials: "include",
    })
    if (res.ok) {
      toast.success("Post deleted")
      loadPosts()
    } else {
      toast.error("Failed to delete post")
    }
  }

  if (!user?.is_superuser) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-muted-foreground text-sm">
        Access denied. Superuser required.
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Blog Management</h1>
          <p className="text-sm text-muted-foreground mt-1">Create and manage blog posts. Content supports Markdown.</p>
        </div>
        <Button onClick={openCreate} className="gap-2 bg-ui-main hover:bg-[#003d8f]">
          <Plus className="h-4 w-4" /> New Post
        </Button>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : posts.length === 0 ? (
        <p className="text-sm text-muted-foreground">No posts yet. Create your first post.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Title</TableHead>
              <TableHead>Tags</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Updated</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {posts.map((post) => (
              <TableRow key={post.id}>
                <TableCell className="font-medium max-w-[200px] truncate">{post.title}</TableCell>
                <TableCell>
                  {post.tags ? (
                    <div className="flex flex-wrap gap-1">
                      {post.tags.split(",").slice(0, 2).map((t) => (
                        <Badge key={t} variant="secondary" className="text-xs">{t.trim()}</Badge>
                      ))}
                    </div>
                  ) : (
                    <span className="text-muted-foreground text-xs">—</span>
                  )}
                </TableCell>
                <TableCell>
                  <Badge variant={post.is_published ? "default" : "outline"} className="text-xs">
                    {post.is_published ? "Published" : "Draft"}
                  </Badge>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground whitespace-nowrap">{formatDate(post.created_at)}</TableCell>
                <TableCell className="text-xs text-muted-foreground whitespace-nowrap">{formatDate(post.updated_at)}</TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    <Button variant="ghost" size="icon" onClick={() => openEdit(post)} title="Edit">
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => deletePost(post)} title="Delete">
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-3xl max-h-[92vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editing ? "Edit Post" : "New Post"}</DialogTitle>
          </DialogHeader>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="title">Title *</Label>
                <Input id="title" {...register("title", { required: "Title is required" })} />
                {errors.title && <p className="text-xs text-destructive">{errors.title.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="slug">Slug *</Label>
                <Input id="slug" {...register("slug", { required: "Slug is required" })} />
                {errors.slug && <p className="text-xs text-destructive">{errors.slug.message}</p>}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="summary">Summary</Label>
                <Input id="summary" placeholder="Short description shown in the list" {...register("summary")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="tags">Tags</Label>
                <Input id="tags" placeholder="Comma-separated: AI, Tutorial, Product" {...register("tags")} />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label htmlFor="content">Content * <span className="text-xs font-normal text-muted-foreground">(Markdown supported)</span></Label>
                <div className="flex items-center gap-1 border rounded-md p-0.5">
                  <button
                    type="button"
                    onClick={() => setContentTab("write")}
                    className={`flex items-center gap-1 px-2.5 py-1 text-xs rounded transition-colors ${
                      contentTab === "write"
                        ? "bg-foreground text-background"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Code2 className="h-3 w-3" /> Write
                  </button>
                  <button
                    type="button"
                    onClick={() => setContentTab("preview")}
                    className={`flex items-center gap-1 px-2.5 py-1 text-xs rounded transition-colors ${
                      contentTab === "preview"
                        ? "bg-foreground text-background"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Eye className="h-3 w-3" /> Preview
                  </button>
                </div>
              </div>

              {contentTab === "write" ? (
                <Textarea
                  id="content"
                  rows={16}
                  placeholder={`Write your post in Markdown…\n\n# Heading\n\n**Bold**, *italic*, \`code\`\n\n- List item`}
                  className="font-mono text-sm resize-y"
                  {...register("content", { required: "Content is required" })}
                />
              ) : (
                <div className="min-h-[280px] rounded-md border p-4 overflow-y-auto prose prose-sm dark:prose-invert max-w-none">
                  {contentValue ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{contentValue}</ReactMarkdown>
                  ) : (
                    <p className="text-muted-foreground text-sm italic">Nothing to preview yet.</p>
                  )}
                </div>
              )}
              {errors.content && <p className="text-xs text-destructive">{errors.content.message}</p>}
            </div>

            <div className="flex items-center gap-3">
              <Switch
                id="is_published"
                checked={watch("is_published")}
                onCheckedChange={(v) => setValue("is_published", v)}
              />
              <Label htmlFor="is_published">Publish immediately</Label>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={saving} className="bg-ui-main hover:bg-[#003d8f]">
                {saving ? "Saving…" : editing ? "Update Post" : "Create Post"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
