"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useRef, useState } from "react"
import { ImageUp, Loader2, Trash2 } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"

/**
 * Superuser-only control for the headshot shown in the public profile hero.
 *
 * Talks to the backend through the same-origin proxy (`/api/proxy/...`) so the
 * HttpOnly auth cookie is exchanged for the Bearer token server-side. Uploads
 * are re-validated by magic bytes on the backend; the checks here are just to
 * fail fast with a friendly message.
 */

const META_URL = "/api/proxy/api/v1/profile/image/meta"
const IMAGE_URL = "/api/proxy/api/v1/profile/image"

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"]
const MAX_BYTES = 5 * 1024 * 1024

interface ProfileImageMeta {
  has_image: boolean
  content_type?: string | null
  updated_at?: string | null
}

async function readError(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json()
    return typeof body?.detail === "string" ? body.detail : fallback
  } catch {
    return fallback
  }
}

const ProfilePhoto = () => {
  const queryClient = useQueryClient()
  const showToast = useToast()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [preview, setPreview] = useState<string | null>(null)

  const { data: meta, isLoading } = useQuery<ProfileImageMeta>({
    queryKey: ["profileImageMeta"],
    queryFn: async () => {
      const res = await fetch(META_URL, { cache: "no-store" })
      if (!res.ok) throw new Error("Failed to load profile photo status")
      return res.json()
    },
  })

  // Cache-busted so a replaced photo shows immediately instead of the old one.
  const currentSrc =
    preview ??
    (meta?.has_image
      ? `${IMAGE_URL}?v=${encodeURIComponent(meta.updated_at ?? "")}`
      : null)

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append("file", file)
      const res = await fetch(IMAGE_URL, { method: "POST", body: formData })
      if (!res.ok) throw new Error(await readError(res, "Upload failed"))
      return res.json() as Promise<ProfileImageMeta>
    },
    onSuccess: () => {
      showToast("Success!", "Profile photo updated.", "success")
    },
    onError: (err: Error) => {
      setPreview(null)
      showToast("Something went wrong.", err.message, "error")
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["profileImageMeta"] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(IMAGE_URL, { method: "DELETE" })
      if (!res.ok) throw new Error(await readError(res, "Delete failed"))
    },
    onSuccess: () => {
      setPreview(null)
      showToast("Removed", "Profile photo removed.", "success")
    },
    onError: (err: Error) => {
      showToast("Something went wrong.", err.message, "error")
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["profileImageMeta"] })
    },
  })

  const onFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    // Allow re-selecting the same file after a failed attempt.
    event.target.value = ""
    if (!file) return

    if (!ACCEPTED_TYPES.includes(file.type)) {
      showToast(
        "Unsupported file",
        "Choose a JPEG, PNG, or WebP image.",
        "error",
      )
      return
    }
    if (file.size > MAX_BYTES) {
      showToast("File too large", "Images must be 5 MB or smaller.", "error")
      return
    }

    setPreview(URL.createObjectURL(file))
    uploadMutation.mutate(file)
  }

  const isBusy = uploadMutation.isPending || deleteMutation.isPending

  return (
    <div className="max-w-full">
      <h3 className="text-sm font-semibold py-4">Profile Photo</h3>
      <p className="text-sm text-muted-foreground mb-6 max-w-prose">
        The headshot shown in the hero of the public profile page. JPEG, PNG, or
        WebP, up to 5&nbsp;MB. A square image works best — it is cropped to a
        circle. With no photo set, the page falls back to an initials ring.
      </p>

      <div className="flex items-center gap-6">
        <div className="relative h-28 w-28 shrink-0 rounded-full bg-gradient-to-br from-ui-accent/20 to-cyan-400/20 p-1.5 ring-1 ring-border">
          {isLoading ? (
            <div className="h-full w-full animate-pulse rounded-full bg-muted" />
          ) : currentSrc ? (
            // Plain <img>: the source is a dynamic API route, and next/image
            // adds nothing for a 112px avatar behind the proxy.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={currentSrc}
              alt="Current profile photo"
              className="h-full w-full rounded-full object-cover"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-[#0f766e] to-[#06b6d4]">
              <span className="text-2xl font-bold tracking-tight text-white">
                PS
              </span>
            </div>
          )}
          {isBusy && (
            <div className="absolute inset-0 flex items-center justify-center rounded-full bg-background/60">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          )}
        </div>

        <div className="flex flex-col gap-3">
          <Label htmlFor="profile-photo-input" className="sr-only">
            Upload a profile photo
          </Label>
          <input
            id="profile-photo-input"
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_TYPES.join(",")}
            onChange={onFileChange}
            className="hidden"
          />
          <div className="flex gap-3">
            <Button
              type="button"
              className="bg-ui-main hover:bg-[#003d8f] text-white"
              onClick={() => fileInputRef.current?.click()}
              disabled={isBusy}
            >
              <ImageUp className="mr-2 h-4 w-4" />
              {meta?.has_image ? "Replace photo" : "Upload photo"}
            </Button>
            {meta?.has_image && (
              <Button
                type="button"
                variant="outline"
                onClick={() => deleteMutation.mutate()}
                disabled={isBusy}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Remove
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ProfilePhoto
